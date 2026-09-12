"""Ollama adapter behind the provider-neutral gateway."""

from __future__ import annotations

import json
import time

import httpx

from app.ai.contracts import (
    ENRICHMENT_SYSTEM_PROMPT,
    EmbeddingRequest,
    EmbeddingResult,
    EnrichmentRequest,
    EnrichmentResult,
    RerankRequest,
    RerankResult,
)
from app.ai.gateway import (
    ProviderCapability,
    ProviderError,
    ProviderErrorCode,
    ProviderHealth,
    ProviderLimits,
    ProviderModel,
    ProviderProvenance,
    ProviderResponse,
    ProviderType,
    ProviderUsage,
)
from app.ai.providers.http import HttpProviderAdapter
from app.ai.providers.openrouter import ENRICHMENT_JSON_SCHEMA


class OllamaAdapter(HttpProviderAdapter):
    provider_type = ProviderType.OLLAMA
    capabilities = frozenset(
        {
            ProviderCapability.ENRICHMENT,
            ProviderCapability.RERANKING,
            ProviderCapability.MODEL_LISTING,
            ProviderCapability.TOKEN_USAGE,
            ProviderCapability.HEALTH,
        }
    )

    def __init__(
        self,
        base_url: str,
        default_model: str,
        embedding_model: str | None = None,
        keep_alive: str = "5m",
        deployment_type: str = "local",
        *,
        client: httpx.AsyncClient | None = None,
        limits: ProviderLimits | None = None,
    ) -> None:
        super().__init__(client)
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.embedding_model = embedding_model
        self.keep_alive = keep_alive
        self.deployment_type = deployment_type
        self.limits = limits or ProviderLimits()
        if embedding_model:
            self.capabilities = self.capabilities | frozenset(
                {ProviderCapability.EMBEDDINGS}
            )

    async def enrich(
        self, request: EnrichmentRequest, *, model: str | None
    ) -> ProviderResponse:
        selected_model = model or self.default_model
        started = time.monotonic()
        response = await self._request(
            "POST",
            f"{self.base_url}/api/generate",
            json={
                "model": selected_model,
                "stream": False,
                "prompt": ENRICHMENT_SYSTEM_PROMPT + "\n\n" + request.contextual_text,
                "format": ENRICHMENT_JSON_SCHEMA["schema"],
                "keep_alive": self.keep_alive,
                "options": {"temperature": 0},
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from exc
        if not isinstance(payload, dict) or not isinstance(
            payload.get("response"), str
        ):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        try:
            generated = json.loads(payload["response"])
            enrichment = EnrichmentResult(
                summary=generated.get("summary"),
                detailed_summary=generated.get("detailed_summary"),
                topics=generated.get("topics", []),
                suggested_tags=generated.get("suggested_tags", []),
                classification=generated.get("classification"),
                entities=generated.get("entities", []),
                key_phrases=generated.get("key_phrases", []),
                content_language=generated.get("content_language"),
                confidence=generated.get("confidence"),
                warnings=generated.get("warnings", []),
                attempted=True,
                succeeded=True,
                provider=self.provider_type.value,
                model=selected_model,
            )
        except (AttributeError, TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None
        if not enrichment.summary:
            raise ProviderError(ProviderErrorCode.CONTENT_REFUSAL, self.provider_type)
        input_tokens = payload.get("prompt_eval_count")
        output_tokens = payload.get("eval_count")
        usage = ProviderUsage(
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            total_tokens=(
                input_tokens + output_tokens
                if isinstance(input_tokens, int) and isinstance(output_tokens, int)
                else None
            ),
        )
        return ProviderResponse(
            enrichment=enrichment,
            usage=usage,
            provenance=ProviderProvenance(
                provider=self.provider_type,
                model=selected_model,
                request_id=response.headers.get("x-request-id"),
                latency_ms=int((time.monotonic() - started) * 1000),
                configured_model=selected_model,
                finish_reason=payload.get("done_reason"),
                routing_policy={"deployment_type": self.deployment_type},
            ),
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if not self.embedding_model or request.model_alias != self.embedding_model:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, self.provider_type)
        response = await self._request(
            "POST",
            f"{self.base_url}/api/embed",
            json={
                "model": self.embedding_model,
                "input": request.text,
                "dimensions": request.expected_dimensions,
                "truncate": True,
                "keep_alive": self.keep_alive,
            },
        )
        try:
            payload = response.json()
            vectors = payload["embeddings"]
            if not isinstance(vectors, list) or len(vectors) != 1:
                raise ValueError
            return EmbeddingResult(
                chunk_id=request.chunk_id,
                model_alias=payload.get("model") or self.embedding_model,
                dimensions=request.expected_dimensions,
                vector=vectors[0],
                provider=self.provider_type.value,
                usage={"input_tokens": payload.get("prompt_eval_count")},
                provenance={"deployment_type": self.deployment_type},
            )
        except (KeyError, TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None

    async def rerank(self, request: RerankRequest) -> RerankResult:
        candidate_ids = [candidate.item_id for candidate in request.candidates]
        schema = {
            "type": "object",
            "properties": {
                "ordered_item_ids": {
                    "type": "array",
                    "items": {"type": "string", "enum": candidate_ids},
                    "minItems": 1,
                    "maxItems": len(candidate_ids),
                    "uniqueItems": True,
                }
            },
            "required": ["ordered_item_ids"],
            "additionalProperties": False,
        }
        candidates = "\n".join(
            f"{candidate.item_id}: {candidate.text}" for candidate in request.candidates
        )
        response = await self._request(
            "POST",
            f"{self.base_url}/api/generate",
            json={
                "model": request.model_alias,
                "stream": False,
                "prompt": (
                    "Rank the candidate IDs by relevance to the query. Return only "
                    f"schema-valid JSON.\nQuery: {request.query}\nCandidates:\n{candidates}"
                ),
                "format": schema,
                "keep_alive": self.keep_alive,
                "options": {"temperature": 0},
            },
        )
        try:
            payload = response.json()
            generated = json.loads(payload["response"])
            ordered = generated["ordered_item_ids"]
            if not isinstance(ordered, list):
                raise ValueError
            result = RerankResult(
                ordered_item_ids=ordered,
                model_alias=request.model_alias,
                provider=self.provider_type.value,
                usage={
                    "input_tokens": payload.get("prompt_eval_count"),
                    "output_tokens": payload.get("eval_count"),
                },
            )
            if not set(result.ordered_item_ids).issubset(candidate_ids):
                raise ValueError
            return result
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None

    async def list_models(self) -> tuple[ProviderModel, ...]:
        response = await self._request("GET", f"{self.base_url}/api/tags")
        try:
            values = response.json().get("models", [])
            return tuple(
                ProviderModel(
                    id=value["name"],
                    capabilities=frozenset({ProviderCapability.ENRICHMENT}),
                )
                for value in values
                if isinstance(value, dict) and isinstance(value.get("name"), str)
            )
        except (AttributeError, ValueError) as exc:
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from exc

    async def health(self) -> ProviderHealth:
        started = time.monotonic()
        models = {model.id for model in await self.list_models()}
        expected = {self.default_model}
        if self.embedding_model:
            expected.add(self.embedding_model)
        available = expected.issubset(models)
        return ProviderHealth(
            available,
            int((time.monotonic() - started) * 1000),
            None if available else "configured Ollama model is unavailable",
        )
