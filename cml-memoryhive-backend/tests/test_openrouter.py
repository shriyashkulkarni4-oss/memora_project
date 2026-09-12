"""OpenRouter connectivity, policy, and provenance tests."""

import json

import httpx
import pytest
from pydantic import SecretStr

from app.ai.contracts import EmbeddingRequest, EnrichmentRequest
from app.ai.factory import build_ai_gateway
from app.ai.gateway import (
    AIGateway,
    ProviderCapability,
    ProviderError,
    ProviderErrorCode,
    ProviderLimits,
    ProviderType,
)
from app.ai.providers.openrouter import OpenRouterAdapter
from app.config import Settings

pytestmark = pytest.mark.asyncio

MODEL = "openai/gpt-test"


def enrichment_payload(**overrides: object) -> dict[str, object]:
    content = {
        "summary": "A valid structured summary.",
        "detailed_summary": None,
        "topics": ["memory"],
        "suggested_tags": ["research"],
        "classification": "article",
        "entities": [],
        "key_phrases": ["structured result"],
        "confidence": 0.9,
        "warnings": [],
    }
    payload: dict[str, object] = {
        "id": "generation-1",
        "model": MODEL,
        "provider": "provider-b",
        "choices": [
            {
                "message": {"content": json.dumps(content)},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
            "cost": 0.0003,
        },
    }
    payload.update(overrides)
    return payload


def adapter(
    client: httpx.AsyncClient,
    *,
    allow_fallbacks: bool = False,
    default_model: str = MODEL,
) -> OpenRouterAdapter:
    return OpenRouterAdapter(
        api_key="openrouter-secret",
        base_url="https://openrouter.test/api/v1",
        default_model=default_model,
        embedding_model="openai/embed-test",
        allowed_models=[MODEL, "openai/embed-test"],
        allowed_providers=["provider-a", "provider-b"],
        allow_fallbacks=allow_fallbacks,
        app_url="https://memoryhive.test",
        app_title="Memoryhive Test",
        client=client,
        limits=ProviderLimits(maximum_attempts=1),
    )


async def test_openrouter_structured_enrichment_and_visible_fallback_provenance() -> (
    None
):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json=enrichment_payload(),
            headers={"x-request-id": "request-header-id"},
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    response = await AIGateway([adapter(client, allow_fallbacks=True)]).enrich(
        ProviderType.OPENROUTER,
        EnrichmentRequest("item-1", 1, "Saved content to analyze."),
    )
    await client.aclose()

    assert response.enrichment.summary == "A valid structured summary."
    assert response.usage.total_tokens == 30
    assert response.usage.estimated_cost_usd == 0.0003
    assert response.provenance.configured_model == MODEL
    assert response.provenance.model == MODEL
    assert response.provenance.resolved_provider == "provider-b"
    assert response.provenance.provider_fallback is True
    assert response.provenance.finish_reason == "stop"
    assert response.provenance.request_id == "request-header-id"
    body = json.loads(seen[0].content)
    assert body["response_format"]["type"] == "json_schema"
    assert body["provider"] == {
        "allow_fallbacks": True,
        "require_parameters": True,
        "data_collection": "deny",
        "only": ["provider-a", "provider-b"],
        "order": ["provider-a", "provider-b"],
    }
    assert seen[0].headers["authorization"] == "Bearer openrouter-secret"
    assert seen[0].headers["http-referer"] == "https://memoryhive.test"
    assert seen[0].headers["x-title"] == "Memoryhive Test"


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, ProviderErrorCode.AUTHENTICATION),
        (429, ProviderErrorCode.RATE_LIMIT),
        (402, ProviderErrorCode.BUDGET_EXCEEDED),
    ],
)
async def test_openrouter_normalizes_key_rate_and_budget_errors(
    status_code: int, expected: ProviderErrorCode
) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, request=request)
        )
    )
    with pytest.raises(ProviderError) as caught:
        await AIGateway([adapter(client)]).enrich(
            ProviderType.OPENROUTER, EnrichmentRequest("item", 1, "content")
        )
    await client.aclose()
    assert caught.value.code == expected
    assert "openrouter-secret" not in str(caught.value)


@pytest.mark.parametrize(
    "payload",
    [
        {"choices": []},
        enrichment_payload(choices=[{"message": {"content": "not-json"}}]),
        enrichment_payload(
            choices=[
                {
                    "message": {"content": "", "refusal": "blocked"},
                    "finish_reason": "content_filter",
                }
            ]
        ),
    ],
)
async def test_openrouter_rejects_malformed_and_refused_responses(
    payload: dict[str, object],
) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload, request=request)
        )
    )
    with pytest.raises(ProviderError) as caught:
        await AIGateway([adapter(client)]).enrich(
            ProviderType.OPENROUTER, EnrichmentRequest("item", 1, "content")
        )
    await client.aclose()
    assert caught.value.code in {
        ProviderErrorCode.MALFORMED_RESPONSE,
        ProviderErrorCode.CONTENT_REFUSAL,
    }


async def test_openrouter_timeout_is_normalized() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out with no credential", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
    with pytest.raises(ProviderError) as caught:
        await AIGateway([adapter(client)]).enrich(
            ProviderType.OPENROUTER, EnrichmentRequest("item", 1, "content")
        )
    await client.aclose()
    assert caught.value.code == ProviderErrorCode.TIMEOUT


async def test_openrouter_embedding_validates_dimensions() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "data": [{"embedding": [0.1, 0.2, 0.3]}],
                    "model": "openai/embed-test",
                    "usage": {"prompt_tokens": 2, "total_tokens": 2},
                },
                request=request,
            )
        )
    )
    result = await AIGateway([adapter(client)]).embed(
        ProviderType.OPENROUTER,
        EmbeddingRequest("chunk-1", "embed this", "openai/embed-test", 3),
    )
    await client.aclose()
    assert result.vector == (0.1, 0.2, 0.3)
    assert result.dimensions == 3


async def test_openrouter_chat_configuration_does_not_imply_embeddings() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: pytest.fail("chat-only adapter attempted embeddings")
        )
    )
    chat_only = OpenRouterAdapter(
        api_key="openrouter-secret",
        base_url="https://openrouter.test/api/v1",
        default_model=MODEL,
        allowed_models=[MODEL],
        client=client,
    )
    assert ProviderCapability.EMBEDDINGS not in chat_only.capabilities
    with pytest.raises(ProviderError) as caught:
        await AIGateway([chat_only]).embed(
            ProviderType.OPENROUTER,
            EmbeddingRequest("chunk-1", "private content", MODEL, 3),
        )
    await client.aclose()
    assert caught.value.code == ProviderErrorCode.UNSUPPORTED_CAPABILITY


async def test_openrouter_health_probe_sends_no_user_content() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": [{"id": MODEL}]}, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    health = await AIGateway([adapter(client)]).health(ProviderType.OPENROUTER)
    await client.aclose()
    assert health.available is True
    assert seen[0].method == "GET"
    assert seen[0].url.path == "/api/v1/models"
    assert seen[0].content == b""


async def test_openrouter_configuration_is_allowlisted_and_explicitly_disabled() -> (
    None
):
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: pytest.fail("disabled OpenRouter made an outbound call")
        )
    )
    gateway = build_ai_gateway(
        Settings(
            database_url="sqlite+aiosqlite://",
            openrouter_enabled=False,
            openrouter_api_key=SecretStr("configured-but-disabled"),
            openrouter_model=MODEL,
            openrouter_allowed_models=[MODEL],
        ),
        client=client,
    )
    assert ProviderType.OPENROUTER not in gateway.adapters
    with pytest.raises(ValueError, match="allowlisted"):
        adapter(client, default_model="arbitrary/not-allowed")
    with pytest.raises(ValueError, match="missing"):
        build_ai_gateway(
            Settings(database_url="sqlite+aiosqlite://", openrouter_enabled=True),
            client=client,
        )
    await client.aclose()
