"""First-class OpenRouter chat, embedding, catalog, and health adapter."""

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

ENRICHMENT_JSON_SCHEMA = {
    "name": "memoryhive_enrichment",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "detailed_summary": {"type": ["string", "null"]},
            "topics": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
            "suggested_tags": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 20,
            },
            "classification": {"type": ["string", "null"]},
            "entities": {"type": "array", "items": {"type": "string"}, "maxItems": 50},
            "key_phrases": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 30,
            },
            "content_language": {"type": ["string", "null"]},
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            "warnings": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        },
        "required": [
            "summary",
            "detailed_summary",
            "topics",
            "suggested_tags",
            "classification",
            "entities",
            "key_phrases",
            "content_language",
            "confidence",
            "warnings",
        ],
    },
}


class OpenRouterAdapter(HttpProviderAdapter):
    provider_type = ProviderType.OPENROUTER
    capabilities = frozenset(
        {
            ProviderCapability.ENRICHMENT,
            ProviderCapability.EMBEDDINGS,
            ProviderCapability.MODEL_LISTING,
            ProviderCapability.TOKEN_USAGE,
            ProviderCapability.HEALTH,
        }
    )

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        default_model: str,
        embedding_model: str | None = None,
        allowed_models: tuple[str, ...] | list[str],
        allowed_providers: tuple[str, ...] | list[str] = (),
        allow_fallbacks: bool = False,
        require_parameters: bool = True,
        data_collection: str = "deny",
        app_url: str | None = None,
        app_title: str | None = None,
        maximum_tokens: int = 800,
        temperature: float = 0.1,
        client: httpx.AsyncClient | None = None,
        limits: ProviderLimits | None = None,
    ) -> None:
        super().__init__(client)
        if not api_key or not default_model:
            raise ValueError("OpenRouter API key and default model are required")
        self.allowed_models = tuple(dict.fromkeys(allowed_models))
        if not self.allowed_models or default_model not in self.allowed_models:
            raise ValueError("OpenRouter default model must be allowlisted")
        if embedding_model and embedding_model not in self.allowed_models:
            raise ValueError("OpenRouter embedding model must be allowlisted")
        if maximum_tokens < 1 or not 0 <= temperature <= 2:
            raise ValueError("OpenRouter generation limits are invalid")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.embedding_model = embedding_model
        if not embedding_model:
            self.capabilities = self.capabilities - frozenset(
                {ProviderCapability.EMBEDDINGS}
            )
        self.allowed_providers = tuple(dict.fromkeys(allowed_providers))
        self.allow_fallbacks = allow_fallbacks
        self.require_parameters = require_parameters
        self.data_collection = data_collection
        self.app_url = app_url
        self.app_title = app_title
        self.maximum_tokens = maximum_tokens
        self.temperature = temperature
        self.limits = limits or ProviderLimits(timeout_seconds=45)

    @property
    def _headers(self) -> dict[str, str]:
        values = {"Authorization": f"Bearer {self.api_key}"}
        if self.app_url:
            values["HTTP-Referer"] = self.app_url
        if self.app_title:
            values["X-Title"] = self.app_title
        return values

    def _validate_model(self, model: str | None) -> str:
        selected = model or self.default_model
        if selected not in self.allowed_models:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, self.provider_type)
        return selected

    @property
    def _routing_policy(self) -> dict[str, object]:
        policy: dict[str, object] = {
            "allow_fallbacks": self.allow_fallbacks,
            "require_parameters": self.require_parameters,
            "data_collection": self.data_collection,
        }
        if self.allowed_providers:
            policy["only"] = list(self.allowed_providers)
            policy["order"] = list(self.allowed_providers)
        return policy

    async def enrich(
        self, request: EnrichmentRequest, *, model: str | None
    ) -> ProviderResponse:
        selected_model = self._validate_model(model)
        started = time.monotonic()
        response = await self._request(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._headers,
            json={
                "model": selected_model,
                "messages": [
                    {
                        "role": "system",
                        "content": ENRICHMENT_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": request.contextual_text},
                ],
                "temperature": self.temperature,
                "max_tokens": self.maximum_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": ENRICHMENT_JSON_SCHEMA,
                },
                "provider": self._routing_policy,
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
        content = message.get("content")
        try:
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
                model=payload.get("model") or selected_model,
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None
        if not enrichment.summary:
            raise ProviderError(ProviderErrorCode.CONTENT_REFUSAL, self.provider_type)
        resolved_model = (
            payload.get("model")
            if isinstance(payload.get("model"), str)
            else selected_model
        )
        resolved_provider = (
            payload.get("provider")
            if isinstance(payload.get("provider"), str)
            else None
        )
        usage = self._usage(payload.get("usage"))
        return ProviderResponse(
            enrichment=enrichment,
            usage=usage,
            provenance=ProviderProvenance(
                provider=self.provider_type,
                model=resolved_model,
                configured_model=selected_model,
                resolved_provider=resolved_provider,
                request_id=response.headers.get("x-request-id") or payload.get("id"),
                latency_ms=int((time.monotonic() - started) * 1000),
                finish_reason=choice.get("finish_reason"),
                routing_policy=self._routing_policy,
                provider_fallback=bool(
                    self.allow_fallbacks
                    and resolved_provider
                    and self.allowed_providers
                    and resolved_provider != self.allowed_providers[0]
                ),
            ),
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if not self.embedding_model or request.model_alias != self.embedding_model:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, self.provider_type)
        selected_model = self._validate_model(request.model_alias)
        response = await self._request(
            "POST",
            f"{self.base_url}/embeddings",
            headers=self._headers,
            json={
                "input": request.text,
                "model": selected_model,
                "dimensions": request.expected_dimensions,
                "encoding_format": "float",
                "provider": self._routing_policy,
            },
        )
        payload = self._json_object(response)
        data = payload.get("data")
        if (
            not isinstance(data, list)
            or len(data) != 1
            or not isinstance(data[0], dict)
        ):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        try:
            return EmbeddingResult(
                chunk_id=request.chunk_id,
                model_alias=payload.get("model") or selected_model,
                dimensions=request.expected_dimensions,
                vector=data[0]["embedding"],
                provider=self.provider_type.value,
            )
        except (KeyError, TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None

    async def list_models(self) -> tuple[ProviderModel, ...]:
        response = await self._request(
            "GET", f"{self.base_url}/models", headers=self._headers
        )
        payload = self._json_object(response)
        data = payload.get("data")
        if not isinstance(data, list):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        return tuple(
            ProviderModel(
                id=value["id"],
                capabilities=frozenset({ProviderCapability.ENRICHMENT}),
            )
            for value in data
            if isinstance(value, dict) and isinstance(value.get("id"), str)
        )

    async def health(self) -> ProviderHealth:
        started = time.monotonic()
        models = await self.list_models()
        available = self.default_model in {model.id for model in models}
        return ProviderHealth(
            available,
            int((time.monotonic() - started) * 1000),
            None if available else "configured model is unavailable",
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

    def _usage(self, value: object) -> ProviderUsage:
        payload = value if isinstance(value, dict) else {}
        try:
            return ProviderUsage(
                input_tokens=payload.get("prompt_tokens"),
                output_tokens=payload.get("completion_tokens"),
                total_tokens=payload.get("total_tokens"),
                estimated_cost_usd=payload.get("cost"),
            )
        except (TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None
