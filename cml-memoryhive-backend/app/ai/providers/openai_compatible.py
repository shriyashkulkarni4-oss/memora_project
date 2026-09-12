"""Restricted adapter for explicitly configured OpenAI-compatible endpoints."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

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

ALLOWED_MODES = {"chat_completions", "responses"}
ALLOWED_EXTRA_OPTIONS = {
    "frequency_penalty",
    "presence_penalty",
    "reasoning_effort",
    "seed",
    "stop",
    "top_p",
}
BLOCKED_HEADERS = {
    "authorization",
    "cookie",
    "host",
    "proxy-authorization",
    "transfer-encoding",
    "x-api-key",
}
METADATA_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.azure.internal",
}


async def resolve_host(hostname: str) -> tuple[str, ...]:
    records = await asyncio.to_thread(
        socket.getaddrinfo, hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
    )
    return tuple(sorted({record[4][0] for record in records}))


class OpenAICompatibleAdapter(HttpProviderAdapter):
    provider_type = ProviderType.OPENAI_COMPATIBLE

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
        default_model: str,
        embedding_model: str | None,
        endpoint_mode: str,
        declared_capabilities: tuple[str, ...] | list[str],
        chat_models: tuple[str, ...] | list[str],
        embedding_models: tuple[str, ...] | list[str],
        allowed_hosts: tuple[str, ...] | list[str],
        allow_private_network: bool = False,
        private_hosts: tuple[str, ...] | list[str] = (),
        extra_headers: dict[str, str] | None = None,
        extra_options: dict[str, object] | None = None,
        maximum_tokens: int = 800,
        temperature: float = 0.1,
        deployment_type: str = "third_party",
        client: httpx.AsyncClient | None = None,
        limits: ProviderLimits | None = None,
        resolver: Callable[[str], Awaitable[tuple[str, ...]]] = resolve_host,
    ) -> None:
        super().__init__(client)
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("OpenAI-compatible base URL must be HTTP(S)")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("OpenAI-compatible base URL contains forbidden components")
        self.hostname = parsed.hostname.lower()
        normalized_hosts = {value.lower() for value in allowed_hosts}
        if self.hostname not in normalized_hosts:
            raise ValueError("OpenAI-compatible base URL host is not allowlisted")
        if self.hostname in METADATA_HOSTS:
            raise ValueError("metadata service destinations are forbidden")
        self.allow_private_network = allow_private_network
        self.private_hosts = {value.lower() for value in private_hosts}
        if parsed.scheme == "http" and not (
            allow_private_network and self.hostname in self.private_hosts
        ):
            raise ValueError(
                "unencrypted compatible endpoints require private-host opt-in"
            )
        self._validate_literal_host()
        if endpoint_mode not in ALLOWED_MODES:
            raise ValueError("unsupported OpenAI-compatible endpoint mode")
        declared: set[ProviderCapability] = set()
        try:
            declared = {ProviderCapability(value) for value in declared_capabilities}
        except ValueError as exc:
            raise ValueError("unknown OpenAI-compatible capability") from exc
        allowed_declared = {
            ProviderCapability.ENRICHMENT,
            ProviderCapability.EMBEDDINGS,
            ProviderCapability.MODEL_LISTING,
            ProviderCapability.TOKEN_USAGE,
            ProviderCapability.HEALTH,
        }
        if not declared.issubset(allowed_declared):
            raise ValueError("unsupported OpenAI-compatible capability")
        self.capabilities = frozenset(declared)
        self.chat_models = tuple(dict.fromkeys(chat_models))
        self.embedding_models = tuple(dict.fromkeys(embedding_models))
        if default_model not in self.chat_models:
            raise ValueError("default chat model must be allowlisted")
        if embedding_model and embedding_model not in self.embedding_models:
            raise ValueError("embedding model must be allowlisted")
        headers = extra_headers or {}
        if any(name.lower() in BLOCKED_HEADERS for name in headers):
            raise ValueError("security-sensitive extra header is forbidden")
        options = extra_options or {}
        if not set(options).issubset(ALLOWED_EXTRA_OPTIONS):
            raise ValueError("unsupported OpenAI-compatible extension option")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.embedding_model = embedding_model
        self.endpoint_mode = endpoint_mode
        self.extra_headers = dict(headers)
        self.extra_options = dict(options)
        self.maximum_tokens = maximum_tokens
        self.temperature = temperature
        self.deployment_type = deployment_type
        self.limits = limits or ProviderLimits()
        self.resolver = resolver

    @property
    def _headers(self) -> dict[str, str]:
        headers = dict(self.extra_headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _validate_literal_host(self) -> None:
        try:
            address = ipaddress.ip_address(self.hostname)
        except ValueError:
            return
        if not address.is_global and not (
            self.allow_private_network and self.hostname in self.private_hosts
        ):
            raise ValueError("private OpenAI-compatible destination is forbidden")

    async def _validate_destination(self) -> None:
        if self.allow_private_network and self.hostname in self.private_hosts:
            return
        try:
            addresses = await self.resolver(self.hostname)
        except (OSError, socket.gaierror):
            raise ProviderError(
                ProviderErrorCode.UNAVAILABLE, self.provider_type
            ) from None
        if not addresses:
            raise ProviderError(ProviderErrorCode.UNAVAILABLE, self.provider_type)
        for value in addresses:
            if not ipaddress.ip_address(value).is_global:
                raise ProviderError(
                    ProviderErrorCode.INVALID_REQUEST, self.provider_type
                )

    def _model(self, value: str | None, allowlist: tuple[str, ...]) -> str:
        selected = value or self.default_model
        if selected not in allowlist:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, self.provider_type)
        return selected

    async def enrich(
        self, request: EnrichmentRequest, *, model: str | None
    ) -> ProviderResponse:
        await self._validate_destination()
        selected = self._model(model, self.chat_models)
        started = time.monotonic()
        common = {
            "model": selected,
            "temperature": self.temperature,
            **self.extra_options,
        }
        if self.endpoint_mode == "chat_completions":
            url = f"{self.base_url}/chat/completions"
            body = {
                **common,
                "messages": [
                    {"role": "system", "content": ENRICHMENT_SYSTEM_PROMPT},
                    {"role": "user", "content": request.contextual_text},
                ],
                "max_tokens": self.maximum_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": ENRICHMENT_JSON_SCHEMA,
                },
            }
        else:
            url = f"{self.base_url}/responses"
            body = {
                **common,
                "instructions": ENRICHMENT_SYSTEM_PROMPT,
                "input": request.contextual_text,
                "max_output_tokens": self.maximum_tokens,
                "text": {
                    "format": {
                        "type": "json_schema",
                        **ENRICHMENT_JSON_SCHEMA,
                    }
                },
            }
        response = await self._request("POST", url, headers=self._headers, json=body)
        payload = self._json_object(response)
        content, finish_reason = self._content(payload)
        try:
            generated = json.loads(content)
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
                model=payload.get("model") or selected,
            )
        except (AttributeError, TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None
        if not enrichment.summary:
            raise ProviderError(ProviderErrorCode.CONTENT_REFUSAL, self.provider_type)
        usage = self._usage(payload.get("usage"))
        return ProviderResponse(
            enrichment=enrichment,
            usage=usage,
            provenance=ProviderProvenance(
                provider=self.provider_type,
                model=payload.get("model") or selected,
                configured_model=selected,
                request_id=response.headers.get("x-request-id") or payload.get("id"),
                latency_ms=int((time.monotonic() - started) * 1000),
                finish_reason=finish_reason,
                routing_policy={
                    "endpoint_mode": self.endpoint_mode,
                    "deployment_type": self.deployment_type,
                },
            ),
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        await self._validate_destination()
        if not self.embedding_model:
            raise ProviderError(
                ProviderErrorCode.UNSUPPORTED_CAPABILITY, self.provider_type
            )
        selected = self._model(request.model_alias, self.embedding_models)
        response = await self._request(
            "POST",
            f"{self.base_url}/embeddings",
            headers=self._headers,
            json={
                "model": selected,
                "input": request.text,
                "dimensions": request.expected_dimensions,
                "encoding_format": "float",
            },
        )
        payload = self._json_object(response)
        try:
            data = payload["data"]
            if not isinstance(data, list) or len(data) != 1:
                raise ValueError
            return EmbeddingResult(
                chunk_id=request.chunk_id,
                model_alias=payload.get("model") or selected,
                dimensions=request.expected_dimensions,
                vector=data[0]["embedding"],
                provider=self.provider_type.value,
                provenance={"deployment_type": self.deployment_type},
            )
        except (KeyError, TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None

    async def list_models(self) -> tuple[ProviderModel, ...]:
        await self._validate_destination()
        response = await self._request(
            "GET", f"{self.base_url}/models", headers=self._headers
        )
        payload = self._json_object(response)
        values = payload.get("data")
        if not isinstance(values, list):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            )
        return tuple(
            ProviderModel(id=value["id"])
            for value in values
            if isinstance(value, dict) and isinstance(value.get("id"), str)
        )

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
            None if available else "configured compatible model is unavailable",
        )

    def _content(self, payload: dict[str, object]) -> tuple[str, str | None]:
        if self.endpoint_mode == "responses":
            content = payload.get("output_text")
            if isinstance(content, str):
                return content, (
                    payload.get("status")
                    if isinstance(payload.get("status"), str)
                    else None
                )
        choices = payload.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                if message.get("refusal"):
                    raise ProviderError(
                        ProviderErrorCode.CONTENT_REFUSAL, self.provider_type
                    )
                content = message.get("content")
                if isinstance(content, str):
                    finish = choices[0].get("finish_reason")
                    return content, finish if isinstance(finish, str) else None
        raise ProviderError(ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type)

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
                input_tokens=payload.get("input_tokens", payload.get("prompt_tokens")),
                output_tokens=payload.get(
                    "output_tokens", payload.get("completion_tokens")
                ),
                total_tokens=payload.get("total_tokens"),
            )
        except (TypeError, ValueError):
            raise ProviderError(
                ProviderErrorCode.MALFORMED_RESPONSE, self.provider_type
            ) from None
