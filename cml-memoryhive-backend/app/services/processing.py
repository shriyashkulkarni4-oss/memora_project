"""Secure, asynchronous content extraction and optional enrichment."""

import asyncio
import ipaddress
import logging
import re
import socket
import time
from dataclasses import replace
from datetime import datetime
from html.parser import HTMLParser
from io import BytesIO
from typing import Awaitable, Callable
from urllib.parse import urljoin, urlparse

import httpx
import pytesseract
from langdetect import DetectorFactory, LangDetectException, detect
from PIL import Image

from app.ai.audit import AIRunContext, AIRunRecorder
from app.ai.budgets import DatabaseBudgetGuard
from app.ai.contracts import (
    AnalysisResult,
    EnrichmentRequest,
    EnrichmentResult,
    ExtractedDocument,
    ExtractionInput,
)
from app.ai.factory import build_ai_gateway
from app.ai.gateway import AIGateway, ProviderError, ProviderType, ProviderUsage
from app.ai.policy import AITask, resolve_task_policy
from app.ai.structured_enrichment import normalize_enrichment
from app.config import Settings, get_settings
from app.models import Item, ItemType, ProcessingJob
from app.observability import (
    AI_CALLS,
    AI_CIRCUIT_OPEN,
    AI_COST,
    AI_FALLBACKS,
    AI_LATENCY,
    AI_TOKENS,
    configured_model_alias,
)
from app.services.storage import StorageService

logger = logging.getLogger(__name__)
DetectorFactory.seed = 0


# Compatibility aliases retained while callers migrate to the canonical names.
ProcessingInput = ExtractionInput
ProcessingResult = AnalysisResult


class UnsafeUrlError(ValueError):
    pass


def normalize_extracted_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def detect_language(value: str) -> str | None:
    if len(value.strip()) < 20:
        return None
    try:
        return detect(value)
    except LangDetectException:
        return None


def fallback_summary(value: str, *, max_sentences: int = 3) -> str | None:
    normalized = normalize_extracted_text(value)
    if not normalized:
        return None
    sentences = [
        part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()
    ]
    if sentences:
        return " ".join(sentences[:max_sentences])[:1200]
    return normalized[:1200]


async def resolve_public_host(hostname: str) -> list[str]:
    try:
        records = await asyncio.to_thread(
            socket.getaddrinfo, hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise UnsafeUrlError("Link host could not be resolved") from exc
    addresses = sorted({record[4][0] for record in records})
    if not addresses:
        raise UnsafeUrlError("Link host could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise UnsafeUrlError("Link resolves to a non-public address")
    return addresses


class ReadableHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: list[str] = []
        self.text: list[str] = []
        self.metadata: dict[str, str] = {}
        self._title_depth = 0
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self._title_depth += 1
        if tag in {"script", "style", "svg", "nav", "footer", "aside"}:
            self._ignored_depth += 1
        if tag == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            content = attributes.get("content", "").strip()
            if key and content:
                self.metadata[key] = content

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        if (
            tag in {"script", "style", "svg", "nav", "footer", "aside"}
            and self._ignored_depth
        ):
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        if self._title_depth:
            self.title.append(value)
        if not self._ignored_depth:
            self.text.append(value)


class SecureLinkFetcher:
    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
        resolver: Callable[[str], Awaitable[list[str]]] = resolve_public_host,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.resolver = resolver

    async def _validate(self, value: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise UnsafeUrlError("Only public HTTP and HTTPS links can be processed")
        if parsed.username or parsed.password:
            raise UnsafeUrlError("Links containing credentials cannot be processed")
        await self.resolver(parsed.hostname)

    async def fetch(self, value: str) -> tuple[str, bytes, str]:
        client = self.client or httpx.AsyncClient(
            timeout=self.settings.processing_fetch_timeout_seconds,
            headers={"User-Agent": "MemoryhiveBot/1.0"},
        )
        close_client = self.client is None
        current = value
        try:
            for _redirect in range(4):
                await self._validate(current)
                async with client.stream(
                    "GET", current, follow_redirects=False
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("Link redirect has no destination")
                        current = urljoin(current, location)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(
                        ";", 1
                    )[0]
                    if content_type not in {"text/html", "text/plain"}:
                        raise ValueError("Link did not return readable text")
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > self.settings.processing_fetch_max_bytes:
                            raise ValueError("Link content exceeds processing limit")
                        chunks.append(chunk)
                    return current, b"".join(chunks), content_type
            raise ValueError("Link redirected too many times")
        finally:
            if close_client:
                await client.aclose()


class ContentProcessor:
    def __init__(
        self,
        storage: StorageService,
        settings: Settings | None = None,
        fetcher: SecureLinkFetcher | None = None,
        ocr: Callable[[Image.Image], str] | None = None,
        enrichment_client: httpx.AsyncClient | None = None,
        ai_gateway: AIGateway | None = None,
        budget_guard: DatabaseBudgetGuard | None = None,
        run_recorder: AIRunRecorder | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.storage = storage
        self.fetcher = fetcher or SecureLinkFetcher(self.settings)
        if self.settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.settings.tesseract_cmd
        self.ocr = ocr or pytesseract.image_to_string
        self.enrichment_client = enrichment_client
        self.ai_gateway = ai_gateway or build_ai_gateway(
            self.settings, client=enrichment_client
        )
        self.budget_guard = budget_guard
        self.run_recorder = run_recorder

    async def process(self, value: ProcessingInput) -> ProcessingResult:
        document = await self.extract(value)
        enrichment = await self.enrich(document, value)
        return AnalysisResult.from_stages(
            document,
            enrichment,
            fallback_summary=fallback_summary(document.extracted_text or ""),
        )

    async def extract(self, value: ExtractionInput) -> ExtractedDocument:
        if value.item_type == ItemType.SCREENSHOT:
            return await self._screenshot(value)
        elif value.item_type == ItemType.LINK and value.url:
            return await self._link(value)
        elif value.item_type == ItemType.TEXT and value.raw_text:
            return self._text(value)
        return ExtractedDocument(
            item_id=value.item_id, analysis_version=value.analysis_version
        )

    def _text(self, value: ExtractionInput) -> ExtractedDocument:
        extracted = normalize_extracted_text(value.raw_text or "")
        return ExtractedDocument(
            item_id=value.item_id,
            analysis_version=value.analysis_version,
            extracted_text=extracted or None,
            normalized_text=extracted.casefold() or None,
            language=detect_language(extracted),
        )

    async def _screenshot(self, value: ExtractionInput) -> ExtractedDocument:
        if not value.asset_keys:
            raise ValueError("Screenshot has no source asset")
        content = await asyncio.to_thread(
            self.storage.get_file_bytes, value.asset_keys[0]
        )

        def run_ocr() -> str:
            with Image.open(BytesIO(content)) as image:
                return self.ocr(image)

        extracted = normalize_extracted_text(await asyncio.to_thread(run_ocr))
        return ExtractedDocument(
            item_id=value.item_id,
            analysis_version=value.analysis_version,
            extracted_text=extracted or None,
            normalized_text=extracted.casefold() or None,
            language=detect_language(extracted),
            metadata={"ocr_engine": "tesseract"},
        )

    async def _link(self, value: ExtractionInput) -> ExtractedDocument:
        url = value.url or ""
        final_url, content, content_type = await self.fetcher.fetch(url)
        text = content.decode("utf-8", errors="replace")
        if content_type == "text/plain":
            extracted = normalize_extracted_text(text)
            return ExtractedDocument(
                item_id=value.item_id,
                analysis_version=value.analysis_version,
                extracted_text=extracted,
                normalized_text=extracted.casefold(),
                language=detect_language(extracted),
                metadata={"resolved_url": final_url},
            )

        parser = ReadableHtmlParser()
        parser.feed(text)
        extracted = normalize_extracted_text("\n".join(parser.text))
        metadata = parser.metadata
        published = metadata.get("article:published_time") or metadata.get("date")
        try:
            published_at = (
                datetime.fromisoformat(published.replace("Z", "+00:00"))
                if published
                else None
            )
        except ValueError:
            published_at = None
        return ExtractedDocument(
            item_id=value.item_id,
            analysis_version=value.analysis_version,
            title=metadata.get("og:title") or " ".join(parser.title) or None,
            description=metadata.get("og:description")
            or metadata.get("description")
            or None,
            author=metadata.get("author") or metadata.get("article:author") or None,
            published_at=published_at,
            favicon_url=urljoin(final_url, "/favicon.ico"),
            extracted_text=extracted or None,
            normalized_text=extracted.casefold() or None,
            language=detect_language(extracted),
            metadata={"resolved_url": final_url},
        )

    async def enrich(
        self, document: ExtractedDocument, value: ExtractionInput
    ) -> EnrichmentResult:
        if (
            not self.settings.ai_structured_enrichment_enabled
            or not document.extracted_text
        ):
            return EnrichmentResult()
        request = EnrichmentRequest(
            item_id=value.item_id,
            analysis_version=value.analysis_version,
            text=document.extracted_text,
            language=document.language,
            notes=value.notes,
        )
        errors: list[str] = []
        audit_context = AIRunContext(
            user_id=value.user_id,
            item_id=value.item_id,
            analysis_version=value.analysis_version,
            job_id=value.analysis_job_id,
            workflow_id=value.workflow_id,
            correlation_id=value.correlation_id,
            fallback_chain=tuple(
                filter(None, [value.ai_provider, *value.ai_fallbacks])
            ),
        )
        provider_order: list[tuple[ProviderType, str | None]] = []
        if value.ai_provider:
            provider_order = [
                (ProviderType(value.ai_provider), value.ai_model),
                *(
                    (
                        ProviderType(provider),
                        model or None,
                    )
                    for route in value.ai_fallbacks
                    for provider, _separator, model in [route.partition(":")]
                ),
            ]
        elif not value.ai_policy_resolved:
            policy = resolve_task_policy(
                self.settings, self.ai_gateway, AITask.ENRICHMENT
            )
            provider_order = (
                [(policy.primary.provider, policy.primary.model)]
                if policy.primary
                else []
            ) + [(route.provider, route.model) for route in policy.fallbacks]
        attempted = False
        for route_index, (provider, model) in enumerate(provider_order):
            attempted = True
            route_started = time.perf_counter()
            reservation = None
            ai_run_id = None
            try:
                if self.run_recorder:
                    ai_run_id = await self.run_recorder.start_model_run(
                        audit_context,
                        task=AITask.ENRICHMENT.value,
                        provider=provider,
                        requested_model=model,
                        content=request.contextual_text,
                        prompt_version="enrichment-v1",
                    )
                if self.budget_guard:
                    reservation = await self.budget_guard.reserve(
                        operation_key=(
                            f"{value.item_id}:v{value.analysis_version}:"
                            f"enrichment:{provider.value}"
                        ),
                        user_id=value.user_id,
                        item_id=value.item_id,
                        task=AITask.ENRICHMENT.value,
                        provider=provider,
                        model=model,
                        estimated_tokens=max(1, len(request.contextual_text) // 4),
                    )
                response = await self.ai_gateway.enrich(
                    provider,
                    request,
                    model=model,
                )
                response = replace(
                    response,
                    enrichment=normalize_enrichment(
                        response.enrichment,
                        source_text=request.text,
                        content_language=document.language,
                        existing_tags=value.existing_tags,
                    ),
                )
                if reservation:
                    await self.budget_guard.complete(reservation, response.usage)
                if ai_run_id and self.run_recorder:
                    await self.run_recorder.complete_model_run(ai_run_id, response)
                    if not response.enrichment.summary:
                        await self.run_recorder.record_deterministic_summary(
                            audit_context,
                            content=request.contextual_text,
                            reason="ungrounded_summary_rejected",
                        )
                usage = response.usage
                model_alias = configured_model_alias(
                    self.settings, provider.value, model
                )
                labels = (provider.value, model_alias, AITask.ENRICHMENT.value)
                AI_CALLS.labels(*labels, "success").inc()
                AI_LATENCY.labels(*labels, "success").observe(
                    (response.provenance.latency_ms / 1000)
                    if response.provenance.latency_ms is not None
                    else time.perf_counter() - route_started
                )
                AI_CIRCUIT_OPEN.labels(provider.value).set(0)
                if route_index > 0 or response.provenance.provider_fallback:
                    AI_FALLBACKS.labels(*labels).inc()
                AI_TOKENS.labels(*labels, "input").inc(usage.input_tokens or 0)
                AI_TOKENS.labels(*labels, "output").inc(usage.output_tokens or 0)
                AI_COST.labels(*labels).inc(usage.estimated_cost_usd or 0)
                return replace(
                    response.enrichment,
                    request_id=response.provenance.request_id,
                    latency_ms=response.provenance.latency_ms,
                    usage={
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "total_tokens": usage.total_tokens,
                        "estimated_cost_usd": usage.estimated_cost_usd,
                    },
                    provenance={
                        "configured_model": response.provenance.configured_model,
                        "resolved_model": response.provenance.model,
                        "resolved_provider": response.provenance.resolved_provider,
                        "finish_reason": response.provenance.finish_reason,
                        "routing_policy": response.provenance.routing_policy,
                        "provider_fallback": response.provenance.provider_fallback,
                        "gateway_fallback": route_index > 0,
                    },
                )
            except ProviderError as exc:
                if reservation:
                    await self.budget_guard.complete(
                        reservation, ProviderUsage(), failed=True
                    )
                if ai_run_id and self.run_recorder:
                    await self.run_recorder.fail_model_run(
                        ai_run_id, error_code=exc.code.value
                    )
                model_alias = configured_model_alias(
                    self.settings, provider.value, model
                )
                labels = (provider.value, model_alias, AITask.ENRICHMENT.value)
                AI_CALLS.labels(*labels, exc.code.value).inc()
                AI_LATENCY.labels(*labels, exc.code.value).observe(
                    time.perf_counter() - route_started
                )
                AI_CIRCUIT_OPEN.labels(provider.value).set(
                    1 if exc.code.value == "circuit_open" else 0
                )
                errors.append(f"{provider.value}:{exc.code.value}")
                logger.warning(
                    "Optional AI enrichment failed: provider=%s code=%s",
                    provider.value,
                    exc.code.value,
                    extra={
                        "correlation_id": value.correlation_id,
                        "job_id": value.analysis_job_id,
                        "workflow_id": value.workflow_id,
                        "provider": provider.value,
                        "stage": "enrichment",
                    },
                )
        if self.run_recorder:
            await self.run_recorder.record_deterministic_summary(
                audit_context,
                content=request.contextual_text,
                reason=errors[-1] if errors else "ai_not_configured",
            )
        return EnrichmentResult(
            content_language=document.language,
            attempted=attempted,
            succeeded=False,
            errors=errors,
        )


def processing_input(item: Item, job: ProcessingJob | None = None) -> ProcessingInput:
    selected_provider = job.ai_provider if job else None
    selected_model = job.ai_model if job else None
    fallbacks: list[str] = []
    if job and isinstance(job.ai_policy, dict):
        routes = [job.ai_policy.get("primary"), *job.ai_policy.get("fallbacks", [])]
        allowed_routes = [
            route
            for route in routes
            if isinstance(route, dict)
            and isinstance(route.get("provider"), str)
            and (
                getattr(item, "_external_ai_allowed", False)
                or not route.get("external", False)
            )
        ]
        if allowed_routes:
            selected_provider = str(allowed_routes[0]["provider"])
            selected_model = (
                str(allowed_routes[0]["model"])
                if allowed_routes[0].get("model")
                else None
            )
            fallbacks = [
                f"{route['provider']}:{route.get('model') or ''}"
                for route in allowed_routes[1:]
            ]
        else:
            selected_provider = None
            selected_model = None
    return ProcessingInput(
        item_id=item.id,
        item_type=ItemType(item.type),
        url=item.url,
        asset_keys=[asset.object_key for asset in item.assets],
        raw_text=item.raw_text,
        notes=item.notes,
        user_id=item.user_id,
        ai_provider=selected_provider,
        ai_model=selected_model,
        ai_fallbacks=fallbacks,
        existing_tags=getattr(item, "_existing_tag_names", ()),
        analysis_job_id=job.id if job else None,
        workflow_id=job.temporal_workflow_id if job else None,
        correlation_id=job.correlation_id if job else None,
        ai_policy_resolved=job is not None,
        analysis_version=item.analysis_version,
    )
