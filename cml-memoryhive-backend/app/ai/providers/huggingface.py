"""Hugging Face Inference Providers chat and feature-extraction adapter."""

from __future__ import annotations

import json
import time
from urllib.parse import quote

import httpx

from app.ai.contracts import (
    ENRICHMENT_SYSTEM_PROMPT,
    EmbeddingRequest,
    EmbeddingResult,
    EnrichmentRequest,
    EnrichmentResult,
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

POLICIES = {"fastest", "cheapest", "preferred"}


class HuggingFaceAdapter(HttpProviderAdapter):
    provider_type = ProviderType.HUGGINGFACE

    def __init__(
        self,
        *,
        token: str,
        router_url: str,
        hub_url: str,
        chat_model: str | None,
        embedding_model: str | None,
        chat_models: tuple[str, ...] | list[str],
        embedding_models: tuple[str, ...] | list[str],
        vision_models: tuple[str, ...] | list[str] = (),
        allowed_policies: tuple[str, ...] | list[str] = tuple(POLICIES),
        allowed_providers: tuple[str, ...] | list[str] = (),
        embedding_dimensions: int | None = None,
        maximum_tokens: int = 800,
        temperature: float = 0.1,
        client: httpx.AsyncClient | None = None,
        limits: ProviderLimits | None = None,
    ) -> None:
        super().__init__(client)
        if not token:
            raise ValueError("Hugging Face inference token is required")
        self.token = token
        self.router_url = router_url.rstrip("/")
        self.hub_url = hub_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.chat_models = tuple(dict.fromkeys(chat_models))
        self.embedding_models = tuple(dict.fromkeys(embedding_models))
        self.vision_models = tuple(dict.fromkeys(vision_models))
        self.allowed_policies = frozenset(allowed_policies)
        self.allowed_providers = frozenset(allowed_providers)
        if not self.allowed_policies.issubset(POLICIES):
            raise ValueError("Unsupported Hugging Face routing policy")
        if chat_model:
            self._validate_model(chat_model, self.chat_models)
        if embedding_model:
            self._validate_model(embedding_model, self.embedding_models)
        if embedding_dimensions is not None and embedding_dimensions < 1:
            raise ValueError("Hugging Face embedding dimensions must be positive")
        self.embedding_dimensions = embedding_dimensions
        self.maximum_tokens = maximum_tokens
        self.temperature = temperature
        self.limits = limits or ProviderLimits(timeout_seconds=60)
        capabilities = {
            ProviderCapability.MODEL_LISTING,
            ProviderCapability.HEALTH,
            ProviderCapability.TOKEN_USAGE,
        }
        if self.chat_models:
            capabilities.add(ProviderCapability.ENRICHMENT)
        if self.embedding_models:
            capabilities.add(ProviderCapability.EMBEDDINGS)
        self.capabilities = frozenset(capabilities)

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _split_model(self, value: str) -> tuple[str, str]:
        if ":" not in value:
            return value, "fastest"
        model, suffix = value.rsplit(":", 1)
        if suffix not in self.allowed_policies and suffix not in self.allowed_providers:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, self.provider_type)
        return model, suffix

    def _validate_model(
        self, value: str, allowlist: tuple[str, ...]
    ) -> tuple[str, str]:
        model, suffix = self._split_model(value)
        if model not in allowlist:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, self.provider_type)
        return model, suffix

    async def enrich(
        self, request: EnrichmentRequest, *, model: str | None
    ) -> ProviderResponse:
        requested = model or self.chat_model
        if not requested:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, self.provider_type)
        base_model, policy = self._validate_model(requested, self.chat_models)
        started = time.monotonic()
        response = await self._request(
            "POST",
            f"{self.router_url}/v1/chat/completions",
            headers=self._headers,
            json={
                "model": requested,
                "messages": [
                    {
                        "role": "system",
                        "content": ENRICHMENT_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": request.contextual_text},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": ENRICHMENT_JSON_SCHEMA,
                },
                "temperature": self.temperature,
                "max_tokens": self.maximum_tokens,
                "stream": False,
            },
        )
        payload = self._json_object(response)
        choices = payload.get("choices")
        if (
            not isinstance(choices, list)
            or not choices
            or not isinstance(choices[0], dict)
        ):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        if message.get("refusal") or choice.get("finish_reason") in {
            "content_filter",
            "refusal",
        }:
            raise ProviderError(ProviderErrorCode.CONTENT_REFUSAL, self.provider_type)
        try:
            content = message.get("content")
            generated = json.loads(content) if isinstance(content, str) else content
            if not isinstance(generated, dict):
                raise ValueError
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
                model=payload.get("model") or requested,
            )
        except (TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None
        if not enrichment.summary:
            raise ProviderError(ProviderErrorCode.CONTENT_REFUSAL, self.provider_type)
        usage_payload = (
            payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        )
        try:
            usage = ProviderUsage(
                input_tokens=usage_payload.get("prompt_tokens"),
                output_tokens=usage_payload.get("completion_tokens"),
                total_tokens=usage_payload.get("total_tokens"),
            )
        except (TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None
        resolved_provider = (
            payload.get("provider")
            if isinstance(payload.get("provider"), str)
            else None
        )
        return ProviderResponse(
            enrichment=enrichment,
            usage=usage,
            provenance=ProviderProvenance(
                provider=self.provider_type,
                model=payload.get("model") or requested,
                configured_model=requested,
                resolved_provider=resolved_provider,
                request_id=response.headers.get("x-request-id") or payload.get("id"),
                latency_ms=int((time.monotonic() - started) * 1000),
                finish_reason=choice.get("finish_reason"),
                routing_policy={"policy_or_provider": policy, "base_model": base_model},
            ),
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        requested = request.model_alias or self.embedding_model
        if not requested:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, self.provider_type)
        model, policy = self._validate_model(requested, self.embedding_models)
        if (
            self.embedding_dimensions
            and request.expected_dimensions != self.embedding_dimensions
        ):
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, self.provider_type)
        response = await self._request(
            "POST",
            (
                f"{self.router_url}/hf-inference/models/{quote(model, safe='/')}"
                "/pipeline/feature-extraction"
            ),
            headers=self._headers,
            json={"inputs": [request.text], "normalize": True, "truncate": True},
        )
        try:
            payload = response.json()
            vector = (
                payload[0]
                if isinstance(payload, list) and len(payload) == 1
                else payload
            )
            return EmbeddingResult(
                chunk_id=request.chunk_id,
                model_alias=requested,
                dimensions=request.expected_dimensions,
                vector=vector,
                provider=self.provider_type.value,
                provenance={
                    "base_model": model,
                    "policy_or_provider": policy,
                    "request_id": response.headers.get("x-request-id"),
                },
            )
        except (IndexError, TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None

    async def list_models(self) -> tuple[ProviderModel, ...]:
        response = await self._request(
            "GET", f"{self.router_url}/v1/models", headers=self._headers
        )
        payload = self._json_object(response)
        values = payload.get("data")
        if not isinstance(values, list):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        return tuple(
            ProviderModel(
                id=value["id"],
                capabilities=frozenset({ProviderCapability.ENRICHMENT}),
            )
            for value in values
            if isinstance(value, dict) and isinstance(value.get("id"), str)
        )

    async def health(self) -> ProviderHealth:
        started = time.monotonic()
        chat_models = {model.id for model in await self.list_models()}
        expected_chat = {self._split_model(value)[0] for value in self.chat_models}
        if self.embedding_model:
            embedding_base, _policy = self._split_model(self.embedding_model)
            response = await self._request(
                "GET",
                f"{self.hub_url}/api/models/{quote(embedding_base, safe='/')}",
                headers=self._headers,
            )
            metadata = self._json_object(response)
            if metadata.get("pipeline_tag") not in {
                "feature-extraction",
                "sentence-similarity",
            }:
                return ProviderHealth(False, message="embedding capability unavailable")
        available = expected_chat.issubset(chat_models)
        return ProviderHealth(
            available,
            int((time.monotonic() - started) * 1000),
            None if available else "configured chat model is unavailable",
        )

    def _json_object(self, response: httpx.Response) -> dict[str, object]:
        try:
            payload = response.json()
        except ValueError:
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None
        if not isinstance(payload, dict):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        return payload
