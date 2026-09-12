"""n8n webhook adapter behind the provider-neutral gateway."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Callable

import httpx

from app.ai.contracts import EnrichmentRequest, EnrichmentResult
from app.ai.gateway import (
    ProviderCapability,
    ProviderError,
    ProviderErrorCode,
    ProviderHealth,
    ProviderLimits,
    ProviderProvenance,
    ProviderResponse,
    ProviderType,
    ProviderUsage,
)
from app.ai.providers.http import HttpProviderAdapter


class N8nAdapter(HttpProviderAdapter):
    provider_type = ProviderType.N8N
    capabilities = frozenset(
        {
            ProviderCapability.ENRICHMENT,
            ProviderCapability.TOKEN_USAGE,
            ProviderCapability.HEALTH,
        }
    )

    def __init__(
        self,
        webhook_url: str,
        api_key: str | None = None,
        signing_secret: str | None = None,
        deployment_type: str = "self_hosted",
        *,
        client: httpx.AsyncClient | None = None,
        limits: ProviderLimits | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        super().__init__(client)
        self.webhook_url = webhook_url
        self.api_key = api_key
        self.signing_secret = signing_secret
        self.deployment_type = deployment_type
        self.clock = clock
        self.limits = limits or ProviderLimits(timeout_seconds=15)

    async def enrich(
        self, request: EnrichmentRequest, *, model: str | None
    ) -> ProviderResponse:
        started = time.monotonic()
        request_payload = {
            "schema_version": request.schema_version,
            "enrichment_rules_version": 1,
            "item_id": request.item_id,
            "analysis_version": request.analysis_version,
            "text": request.contextual_text,
            "language": request.language,
        }
        body = json.dumps(
            request_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.signing_secret:
            timestamp = str(int(self.clock()))
            digest = hmac.new(
                self.signing_secret.encode("utf-8"),
                timestamp.encode("ascii") + b"." + body,
                hashlib.sha256,
            ).hexdigest()
            headers["X-Memoryhive-Timestamp"] = timestamp
            headers["X-Memoryhive-Signature"] = f"sha256={digest}"
        response = await self._request(
            "POST",
            self.webhook_url,
            headers=headers,
            content=body,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        if payload.get("schema_version") != request.schema_version:
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        try:
            enrichment = EnrichmentResult(
                summary=payload.get("summary"),
                detailed_summary=payload.get("detailed_summary"),
                topics=payload.get("topics", []),
                suggested_tags=payload.get("tags", []),
                classification=payload.get("classification"),
                entities=payload.get("entities", []),
                key_phrases=payload.get("key_phrases", []),
                content_language=payload.get("content_language"),
                confidence=payload.get("confidence"),
                warnings=payload.get("warnings", []),
                attempted=True,
                succeeded=True,
                provider=self.provider_type.value,
                model=model,
            )
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from exc
        if not any(
            (
                enrichment.summary,
                enrichment.detailed_summary,
                enrichment.topics,
                enrichment.suggested_tags,
                enrichment.classification,
                enrichment.entities,
                enrichment.key_phrases,
            )
        ):
            raise ProviderError(ProviderErrorCode.CONTENT_REFUSAL, self.provider_type)
        usage_payload = (
            payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        )
        return ProviderResponse(
            enrichment=enrichment,
            usage=ProviderUsage(
                input_tokens=usage_payload.get("input_tokens"),
                output_tokens=usage_payload.get("output_tokens"),
                total_tokens=usage_payload.get("total_tokens"),
                estimated_cost_usd=usage_payload.get("estimated_cost_usd"),
            ),
            provenance=ProviderProvenance(
                provider=self.provider_type,
                model=model,
                request_id=response.headers.get("x-request-id"),
                latency_ms=int((time.monotonic() - started) * 1000),
                routing_policy={"deployment_type": self.deployment_type},
            ),
        )

    async def health(self) -> ProviderHealth:
        # A webhook has no side-effect-free discovery endpoint. Configuration is
        # considered ready; actual delivery health is measured on enrichment.
        return ProviderHealth(True, message="configured")
