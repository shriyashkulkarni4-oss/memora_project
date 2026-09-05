"""Secure, asynchronous content extraction and optional enrichment."""

import asyncio
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from io import BytesIO
from typing import Any, Awaitable, Callable
from urllib.parse import urljoin, urlparse

import httpx
import pytesseract
from langdetect import DetectorFactory, LangDetectException, detect
from PIL import Image

from app.config import Settings, get_settings
from app.models import Item, ItemType, ProcessingJob
from app.services.storage import StorageService

logger = logging.getLogger(__name__)
DetectorFactory.seed = 0


@dataclass
class ProcessingInput:
    item_id: str
    item_type: ItemType
    url: str | None
    asset_keys: list[str]


@dataclass
class ProcessingResult:
    title: str | None = None
    description: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    favicon_url: str | None = None
    extracted_text: str | None = None
    normalized_text: str | None = None
    language: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


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
    ) -> None:
        self.settings = settings or get_settings()
        self.storage = storage
        self.fetcher = fetcher or SecureLinkFetcher(self.settings)
        if self.settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.settings.tesseract_cmd
        self.ocr = ocr or pytesseract.image_to_string

    async def process(self, value: ProcessingInput) -> ProcessingResult:
        if value.item_type == ItemType.SCREENSHOT:
            result = await self._screenshot(value)
        elif value.item_type == ItemType.LINK and value.url:
            result = await self._link(value.url)
        else:
            return ProcessingResult()
        await self._optional_enrichment(result)
        return result

    async def _screenshot(self, value: ProcessingInput) -> ProcessingResult:
        if not value.asset_keys:
            raise ValueError("Screenshot has no source asset")
        content = await asyncio.to_thread(
            self.storage.get_file_bytes, value.asset_keys[0]
        )

        def run_ocr() -> str:
            with Image.open(BytesIO(content)) as image:
                return self.ocr(image)

        extracted = normalize_extracted_text(await asyncio.to_thread(run_ocr))
        return ProcessingResult(
            extracted_text=extracted or None,
            normalized_text=extracted.casefold() or None,
            language=detect_language(extracted),
            metadata={"ocr_engine": "tesseract"},
        )

    async def _link(self, url: str) -> ProcessingResult:
        final_url, content, content_type = await self.fetcher.fetch(url)
        text = content.decode("utf-8", errors="replace")
        if content_type == "text/plain":
            extracted = normalize_extracted_text(text)
            return ProcessingResult(
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
        return ProcessingResult(
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

    async def _optional_enrichment(self, result: ProcessingResult) -> None:
        if not result.extracted_text:
            return
        if self.settings.ollama_base_url:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        f"{self.settings.ollama_base_url.rstrip('/')}/api/generate",
                        json={
                            "model": self.settings.ollama_model,
                            "stream": False,
                            "prompt": "Summarize in at most three sentences:\n\n"
                            + result.extracted_text[:12000],
                        },
                    )
                    response.raise_for_status()
                    result.summary = response.json().get("response") or None
            except Exception:
                logger.warning("Optional Ollama enrichment failed", exc_info=True)
        if self.settings.n8n_webhook_url:
            try:
                headers = (
                    {"Authorization": f"Bearer {self.settings.n8n_api_key}"}
                    if self.settings.n8n_api_key
                    else {}
                )
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.post(
                        self.settings.n8n_webhook_url,
                        headers=headers,
                        json={
                            "text": result.extracted_text[:50000],
                            "language": result.language,
                        },
                    )
                    response.raise_for_status()
                    enrichment = response.json()
                    result.summary = enrichment.get("summary") or result.summary
                    result.metadata["suggested_tags"] = enrichment.get("tags", [])[:20]
                    result.metadata["classification"] = enrichment.get("classification")
            except Exception:
                logger.warning("Optional n8n enrichment failed", exc_info=True)


def processing_input(item: Item) -> ProcessingInput:
    return ProcessingInput(
        item_id=item.id,
        item_type=ItemType(item.type),
        url=item.url,
        asset_keys=[asset.object_key for asset in item.assets],
    )


def enqueue_processing_job(
    item: Item, max_attempts: int | None = None
) -> ProcessingJob:
    return ProcessingJob(
        item_id=item.id,
        kind=ItemType(item.type).value,
        max_attempts=max_attempts or get_settings().processing_max_attempts,
    )
