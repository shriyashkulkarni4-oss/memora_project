"""Provider gateway policy and adapter conformance tests."""

from dataclasses import dataclass

import httpx
import pytest

from app.ai.contracts import EmbeddingRequest, EnrichmentRequest, EnrichmentResult
from app.ai.gateway import (
    AIGateway,
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
from app.ai.providers import N8nAdapter, OllamaAdapter

pytestmark = pytest.mark.asyncio


def request(text: str = "Analyze this provider-neutral content.") -> EnrichmentRequest:
    return EnrichmentRequest(item_id="item-1", analysis_version=1, text=text)


@dataclass
class FakeAdapter:
    provider_type: ProviderType = ProviderType.OPENROUTER
    capabilities: frozenset[ProviderCapability] = frozenset(
        {ProviderCapability.ENRICHMENT}
    )
    limits: ProviderLimits = ProviderLimits(maximum_attempts=3)
    failures: list[Exception] | None = None
    calls: int = 0

    async def enrich(
        self, _request: EnrichmentRequest, *, model: str | None
    ) -> ProviderResponse:
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return ProviderResponse(
            enrichment=EnrichmentResult(
                summary="Normalized",
                attempted=True,
                succeeded=True,
                provider=self.provider_type.value,
                model=model,
            ),
            usage=ProviderUsage(input_tokens=4, output_tokens=2, total_tokens=6),
            provenance=ProviderProvenance(self.provider_type, model, "request-1", 12),
        )

    async def embed(self, _request: EmbeddingRequest):
        raise ProviderError(
            ProviderErrorCode.UNSUPPORTED_CAPABILITY, self.provider_type
        )

    async def list_models(self) -> tuple[ProviderModel, ...]:
        return ()

    async def health(self) -> ProviderHealth:
        return ProviderHealth(True)


async def test_gateway_retries_only_normalized_retryable_errors() -> None:
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    adapter = FakeAdapter(
        failures=[
            ProviderError(ProviderErrorCode.RATE_LIMIT, ProviderType.OPENROUTER),
            ProviderError(ProviderErrorCode.TIMEOUT, ProviderType.OPENROUTER),
        ]
    )
    gateway = AIGateway([adapter], sleep=sleep, jitter=lambda _a, _b: 0)

    response = await gateway.enrich(ProviderType.OPENROUTER, request(), model="model")

    assert response.enrichment.summary == "Normalized"
    assert adapter.calls == 3
    assert delays == [0.5, 1.0]


async def test_gateway_preflight_rejects_capability_and_payload_before_call() -> None:
    adapter = FakeAdapter(
        capabilities=frozenset(),
        limits=ProviderLimits(maximum_payload_bytes=4),
    )
    gateway = AIGateway([adapter])
    with pytest.raises(ProviderError) as unsupported:
        await gateway.enrich(ProviderType.OPENROUTER, request())
    assert unsupported.value.code == ProviderErrorCode.UNSUPPORTED_CAPABILITY
    assert adapter.calls == 0

    adapter.capabilities = frozenset({ProviderCapability.ENRICHMENT})
    with pytest.raises(ProviderError) as oversized:
        await gateway.enrich(ProviderType.OPENROUTER, request("too large"))
    assert oversized.value.code == ProviderErrorCode.INVALID_REQUEST
    assert adapter.calls == 0


async def test_gateway_sanitizes_unknown_errors_and_opens_circuit() -> None:
    secret = "secret-api-key-must-not-leak"
    adapter = FakeAdapter(
        limits=ProviderLimits(maximum_attempts=1, circuit_failure_threshold=1),
        failures=[RuntimeError(secret)],
    )
    gateway = AIGateway([adapter], clock=lambda: 10)

    with pytest.raises(ProviderError) as failed:
        await gateway.enrich(ProviderType.OPENROUTER, request())
    assert failed.value.code == ProviderErrorCode.UNAVAILABLE
    assert secret not in str(failed.value)

    with pytest.raises(ProviderError) as opened:
        await gateway.enrich(ProviderType.OPENROUTER, request())
    assert opened.value.code == ProviderErrorCode.CIRCUIT_OPEN
    assert adapter.calls == 1


@pytest.mark.parametrize("provider", [ProviderType.OLLAMA, ProviderType.N8N])
async def test_built_in_adapter_conformance(provider: ProviderType) -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        if provider == ProviderType.OLLAMA:
            return httpx.Response(
                200,
                json={
                    "response": '{"summary":"Ollama summary"}',
                    "prompt_eval_count": 8,
                    "eval_count": 3,
                },
                headers={"x-request-id": "ollama-request"},
                request=http_request,
            )
        return httpx.Response(
            200,
            json={
                "schema_version": 1,
                "summary": "n8n summary",
                "topics": ["memory"],
                "usage": {"input_tokens": 7, "output_tokens": 2, "total_tokens": 9},
            },
            headers={"x-request-id": "n8n-request"},
            request=http_request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = (
        OllamaAdapter("https://ollama.test", "test-model", client=client)
        if provider == ProviderType.OLLAMA
        else N8nAdapter("https://n8n.test/hook", "private-key", client=client)
    )
    response = await AIGateway([adapter]).enrich(provider, request())
    await client.aclose()

    assert response.enrichment.succeeded is True
    assert response.enrichment.provider == provider.value
    assert response.usage.total_tokens in {9, 11}
    assert response.provenance.provider == provider
    assert response.provenance.request_id
    assert response.provenance.latency_ms is not None


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, ProviderErrorCode.AUTHENTICATION),
        (403, ProviderErrorCode.AUTHORIZATION),
        (429, ProviderErrorCode.RATE_LIMIT),
        (500, ProviderErrorCode.UNAVAILABLE),
        (400, ProviderErrorCode.INVALID_REQUEST),
    ],
)
async def test_http_adapters_share_normalized_status_taxonomy(
    status_code: int, expected: ProviderErrorCode
) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda value: httpx.Response(status_code, request=value)
        )
    )
    adapter = N8nAdapter(
        "https://n8n.test/hook",
        "credential-never-in-error",
        client=client,
        limits=ProviderLimits(maximum_attempts=1),
    )
    with pytest.raises(ProviderError) as caught:
        await AIGateway([adapter]).enrich(ProviderType.N8N, request())
    await client.aclose()

    assert caught.value.code == expected
    assert "credential-never-in-error" not in str(caught.value)
