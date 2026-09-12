"""Provider-neutral AI gateway contracts, policies, and failure isolation."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, Protocol, TypeVar

from app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult,
    EnrichmentRequest,
    EnrichmentResult,
)


class ProviderType(str, Enum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"
    N8N = "n8n"
    OPENAI_COMPATIBLE = "openai_compatible"


class ProviderCapability(str, Enum):
    ENRICHMENT = "enrichment"
    EMBEDDINGS = "embeddings"
    VISION = "vision"
    MODEL_LISTING = "model_listing"
    TOKEN_USAGE = "token_usage"
    HEALTH = "health"


class ProviderErrorCode(str, Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    MALFORMED_RESPONSE = "malformed_response"
    CONTENT_REFUSAL = "content_refusal"
    BUDGET_EXCEEDED = "budget_exceeded"
    CIRCUIT_OPEN = "circuit_open"


RETRYABLE_ERRORS = {
    ProviderErrorCode.RATE_LIMIT,
    ProviderErrorCode.TIMEOUT,
    ProviderErrorCode.UNAVAILABLE,
}


class ProviderError(RuntimeError):
    """A normalized, credential-safe provider failure."""

    def __init__(
        self,
        code: ProviderErrorCode,
        provider: ProviderType,
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        self.code = code
        self.provider = provider
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"{provider.value} provider error: {code.value}")

    @property
    def retryable(self) -> bool:
        return self.code in RETRYABLE_ERRORS


@dataclass(frozen=True)
class ProviderLimits:
    concurrency: int = 4
    timeout_seconds: float = 30
    maximum_payload_bytes: int = 512_000
    maximum_attempts: int = 3
    circuit_failure_threshold: int = 5
    circuit_reset_seconds: float = 60

    def __post_init__(self) -> None:
        if self.concurrency < 1 or self.timeout_seconds <= 0:
            raise ValueError("provider concurrency and timeout must be positive")
        if self.maximum_payload_bytes < 1 or self.maximum_attempts < 1:
            raise ValueError("provider payload and attempt limits must be positive")
        if self.circuit_failure_threshold < 1 or self.circuit_reset_seconds <= 0:
            raise ValueError("provider circuit-breaker limits must be positive")


@dataclass(frozen=True)
class ProviderUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None

    def __post_init__(self) -> None:
        values = (self.input_tokens, self.output_tokens, self.total_tokens)
        if any(
            value is not None and (not isinstance(value, int) or value < 0)
            for value in values
        ):
            raise ValueError("token usage values must be non-negative integers")
        if self.estimated_cost_usd is not None and self.estimated_cost_usd < 0:
            raise ValueError("estimated cost cannot be negative")


@dataclass(frozen=True)
class ProviderProvenance:
    provider: ProviderType
    model: str | None
    request_id: str | None = None
    latency_ms: int | None = None
    configured_model: str | None = None
    resolved_provider: str | None = None
    finish_reason: str | None = None
    routing_policy: dict[str, object] = field(default_factory=dict)
    provider_fallback: bool = False


@dataclass(frozen=True)
class ProviderResponse:
    enrichment: EnrichmentResult
    usage: ProviderUsage
    provenance: ProviderProvenance


@dataclass(frozen=True)
class VisionRequest:
    item_id: str
    media_type: str
    content: bytes
    prompt: str
    model: str | None = None


@dataclass(frozen=True)
class VisionResponse:
    text: str
    usage: ProviderUsage
    provenance: ProviderProvenance


@dataclass(frozen=True)
class ProviderHealth:
    available: bool
    latency_ms: int | None = None
    message: str | None = None


@dataclass(frozen=True)
class ProviderModel:
    id: str
    capabilities: frozenset[ProviderCapability] = field(default_factory=frozenset)


class ProviderAdapter(Protocol):
    provider_type: ProviderType
    capabilities: frozenset[ProviderCapability]
    limits: ProviderLimits

    async def enrich(
        self, request: EnrichmentRequest, *, model: str | None
    ) -> ProviderResponse: ...

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...

    async def vision(self, request: VisionRequest) -> VisionResponse: ...

    async def list_models(self) -> tuple[ProviderModel, ...]: ...

    async def health(self) -> ProviderHealth: ...


@dataclass
class _CircuitState:
    failures: int = 0
    open_until: float = 0


T = TypeVar("T")


class AIGateway:
    """Applies common capability, retry, concurrency, and circuit policies."""

    def __init__(
        self,
        adapters: tuple[ProviderAdapter, ...] | list[ProviderAdapter],
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        jitter: Callable[[float, float], float] = random.uniform,
    ) -> None:
        self.adapters = {adapter.provider_type: adapter for adapter in adapters}
        if len(self.adapters) != len(adapters):
            raise ValueError("provider types must be unique")
        self._semaphores = {
            provider: asyncio.Semaphore(adapter.limits.concurrency)
            for provider, adapter in self.adapters.items()
        }
        self._circuits = {provider: _CircuitState() for provider in self.adapters}
        self._sleep = sleep
        self._clock = clock
        self._jitter = jitter

    def require_capability(
        self, provider: ProviderType, capability: ProviderCapability
    ) -> ProviderAdapter:
        adapter = self.adapters.get(provider)
        if adapter is None or capability not in adapter.capabilities:
            raise ProviderError(ProviderErrorCode.UNSUPPORTED_CAPABILITY, provider)
        return adapter

    async def enrich(
        self,
        provider: ProviderType,
        request: EnrichmentRequest,
        *,
        model: str | None = None,
    ) -> ProviderResponse:
        adapter = self.require_capability(provider, ProviderCapability.ENRICHMENT)
        payload_size = len(request.contextual_text.encode("utf-8"))
        if payload_size > adapter.limits.maximum_payload_bytes:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, provider)
        response = await self._execute(
            provider,
            ProviderCapability.ENRICHMENT,
            lambda: adapter.enrich(request, model=model),
        )
        if response.provenance.provider != provider:
            raise ProviderError(ProviderErrorCode.MALFORMED_RESPONSE, provider)
        return response

    async def embed(
        self, provider: ProviderType, request: EmbeddingRequest
    ) -> EmbeddingResult:
        adapter = self.require_capability(provider, ProviderCapability.EMBEDDINGS)
        if len(request.text.encode("utf-8")) > adapter.limits.maximum_payload_bytes:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, provider)
        return await self._execute(
            provider, ProviderCapability.EMBEDDINGS, lambda: adapter.embed(request)
        )

    async def vision(
        self, provider: ProviderType, request: VisionRequest
    ) -> VisionResponse:
        adapter = self.require_capability(provider, ProviderCapability.VISION)
        if len(request.content) > adapter.limits.maximum_payload_bytes:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, provider)
        response = await self._execute(
            provider, ProviderCapability.VISION, lambda: adapter.vision(request)
        )
        if response.provenance.provider != provider:
            raise ProviderError(ProviderErrorCode.MALFORMED_RESPONSE, provider)
        return response

    async def list_models(self, provider: ProviderType) -> tuple[ProviderModel, ...]:
        adapter = self.require_capability(provider, ProviderCapability.MODEL_LISTING)
        return await self._execute(
            provider, ProviderCapability.MODEL_LISTING, adapter.list_models
        )

    async def health(self, provider: ProviderType) -> ProviderHealth:
        adapter = self.require_capability(provider, ProviderCapability.HEALTH)
        return await self._execute(provider, ProviderCapability.HEALTH, adapter.health)

    async def _execute(
        self,
        provider: ProviderType,
        capability: ProviderCapability,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        adapter = self.require_capability(provider, capability)
        circuit = self._circuits[provider]
        if circuit.open_until > self._clock():
            raise ProviderError(ProviderErrorCode.CIRCUIT_OPEN, provider)

        async with self._semaphores[provider]:
            for attempt in range(1, adapter.limits.maximum_attempts + 1):
                try:
                    async with asyncio.timeout(adapter.limits.timeout_seconds):
                        response = await operation()
                    circuit.failures = 0
                    circuit.open_until = 0
                    return response
                except TimeoutError as exc:
                    error = ProviderError(ProviderErrorCode.TIMEOUT, provider)
                    if attempt >= adapter.limits.maximum_attempts:
                        self._record_failure(provider)
                        raise error from exc
                except ProviderError as exc:
                    error = exc
                    if (
                        not error.retryable
                        or attempt >= adapter.limits.maximum_attempts
                    ):
                        self._record_failure(provider)
                        raise
                except Exception:
                    error = ProviderError(ProviderErrorCode.UNAVAILABLE, provider)
                    if attempt >= adapter.limits.maximum_attempts:
                        self._record_failure(provider)
                        raise error from None
                delay = error.retry_after_seconds or min(
                    8.0, 0.5 * (2 ** (attempt - 1))
                )
                await self._sleep(delay + self._jitter(0, delay / 4))
        raise AssertionError("provider retry loop did not return or raise")

    def _record_failure(self, provider: ProviderType) -> None:
        adapter = self.adapters[provider]
        circuit = self._circuits[provider]
        circuit.failures += 1
        if circuit.failures >= adapter.limits.circuit_failure_threshold:
            circuit.open_until = self._clock() + adapter.limits.circuit_reset_seconds
