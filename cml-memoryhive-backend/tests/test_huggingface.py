"""Hugging Face Inference Providers adapter regression tests."""

import json

import httpx
import pytest
from pydantic import SecretStr

from app.ai.contracts import EmbeddingRequest, EnrichmentRequest
from app.ai.factory import build_ai_gateway
from app.ai.gateway import (
    AIGateway,
    ProviderError,
    ProviderErrorCode,
    ProviderLimits,
    ProviderType,
)
from app.ai.providers.huggingface import HuggingFaceAdapter
from app.config import Settings

pytestmark = pytest.mark.asyncio

CHAT_MODEL = "openai/gpt-oss-test"
EMBED_MODEL = "sentence-transformers/test-embed"


def adapter(client: httpx.AsyncClient) -> HuggingFaceAdapter:
    return HuggingFaceAdapter(
        token="hf_inference_only_secret",
        router_url="https://router.huggingface.test",
        hub_url="https://huggingface.test",
        chat_model=f"{CHAT_MODEL}:preferred",
        embedding_model=f"{EMBED_MODEL}:hf-inference",
        chat_models=[CHAT_MODEL],
        embedding_models=[EMBED_MODEL],
        vision_models=["vision/model"],
        allowed_providers=["hf-inference", "together"],
        embedding_dimensions=3,
        client=client,
        limits=ProviderLimits(maximum_attempts=1),
    )


def chat_response() -> dict[str, object]:
    result = {
        "summary": "Hosted open-model summary.",
        "detailed_summary": None,
        "topics": ["open models"],
        "suggested_tags": ["hugging-face"],
        "classification": "note",
        "entities": ["Hugging Face"],
        "key_phrases": ["inference providers"],
        "confidence": 0.8,
        "warnings": [],
    }
    return {
        "id": "hf-request",
        "model": f"{CHAT_MODEL}:preferred",
        "provider": "together",
        "choices": [
            {"message": {"content": json.dumps(result)}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
    }


async def test_huggingface_chat_enrichment_records_policy_and_provider() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=chat_response(), request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    response = await AIGateway([adapter(client)]).enrich(
        ProviderType.HUGGINGFACE,
        EnrichmentRequest("item", 1, "Analyze this open-model content."),
    )
    await client.aclose()

    assert response.enrichment.summary == "Hosted open-model summary."
    assert response.usage.total_tokens == 14
    assert response.provenance.resolved_provider == "together"
    assert response.provenance.routing_policy == {
        "policy_or_provider": "preferred",
        "base_model": CHAT_MODEL,
    }
    assert seen[0].url.path == "/v1/chat/completions"
    assert json.loads(seen[0].content)["model"] == f"{CHAT_MODEL}:preferred"


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        ("fastest", "fastest"),
        ("cheapest", "cheapest"),
        ("preferred", "preferred"),
        ("together", "together"),
    ],
)
async def test_huggingface_policy_and_named_provider_suffixes(
    suffix: str, expected: str
) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=chat_response(), request=request)
        )
    )
    response = await AIGateway([adapter(client)]).enrich(
        ProviderType.HUGGINGFACE,
        EnrichmentRequest("item", 1, "content"),
        model=f"{CHAT_MODEL}:{suffix}",
    )
    await client.aclose()
    assert response.provenance.routing_policy["policy_or_provider"] == expected


async def test_huggingface_feature_extraction_has_stable_dimensions() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json=[[0.1, 0.2, 0.3]],
            headers={"x-request-id": "embedding-request"},
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await AIGateway([adapter(client)]).embed(
        ProviderType.HUGGINGFACE,
        EmbeddingRequest("chunk", "embed me", f"{EMBED_MODEL}:hf-inference", 3),
    )
    await client.aclose()

    assert result.vector == (0.1, 0.2, 0.3)
    assert result.provenance["policy_or_provider"] == "hf-inference"
    assert seen[0].url.path.endswith(
        f"/models/{EMBED_MODEL}/pipeline/feature-extraction"
    )
    assert json.loads(seen[0].content) == {
        "inputs": ["embed me"],
        "normalize": True,
        "truncate": True,
    }


async def test_huggingface_dimension_change_is_malformed() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=[[0.1, 0.2]], request=request)
        )
    )
    with pytest.raises(ProviderError) as caught:
        await AIGateway([adapter(client)]).embed(
            ProviderType.HUGGINGFACE,
            EmbeddingRequest("chunk", "embed me", f"{EMBED_MODEL}:hf-inference", 3),
        )
    await client.aclose()
    assert caught.value.code == ProviderErrorCode.MALFORMED_RESPONSE


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, ProviderErrorCode.AUTHENTICATION),
        (429, ProviderErrorCode.RATE_LIMIT),
        (503, ProviderErrorCode.UNAVAILABLE),
        (504, ProviderErrorCode.UNAVAILABLE),
    ],
)
async def test_huggingface_cold_auth_rate_and_unavailable_errors(
    status_code: int, expected: ProviderErrorCode
) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, request=request)
        )
    )
    with pytest.raises(ProviderError) as caught:
        await AIGateway([adapter(client)]).enrich(
            ProviderType.HUGGINGFACE, EnrichmentRequest("item", 1, "content")
        )
    await client.aclose()
    assert caught.value.code == expected
    assert "hf_inference_only_secret" not in str(caught.value)


async def test_huggingface_malformed_output_and_unknown_provider_are_rejected() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"choices": [{"message": {"content": "{"}}]}, request=request
            )
        )
    )
    gateway = AIGateway([adapter(client)])
    with pytest.raises(ProviderError) as malformed:
        await gateway.enrich(
            ProviderType.HUGGINGFACE, EnrichmentRequest("item", 1, "content")
        )
    with pytest.raises(ProviderError) as unknown:
        await gateway.enrich(
            ProviderType.HUGGINGFACE,
            EnrichmentRequest("item", 1, "content"),
            model=f"{CHAT_MODEL}:unapproved-provider",
        )
    await client.aclose()
    assert malformed.value.code == ProviderErrorCode.MALFORMED_RESPONSE
    assert unknown.value.code == ProviderErrorCode.INVALID_REQUEST


async def test_huggingface_health_uses_only_catalog_metadata() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "router.huggingface.test":
            return httpx.Response(
                200, json={"data": [{"id": CHAT_MODEL}]}, request=request
            )
        return httpx.Response(
            200,
            json={"id": EMBED_MODEL, "pipeline_tag": "feature-extraction"},
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    health = await AIGateway([adapter(client)]).health(ProviderType.HUGGINGFACE)
    await client.aclose()
    assert health.available is True
    assert all(request.method == "GET" and request.content == b"" for request in seen)


async def test_huggingface_is_explicitly_enabled_and_requires_task_models() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: pytest.fail("disabled Hugging Face made a request")
        )
    )
    gateway = build_ai_gateway(
        Settings(
            database_url="sqlite+aiosqlite://",
            huggingface_enabled=False,
            huggingface_token=SecretStr("configured-but-disabled"),
        ),
        client=client,
    )
    assert ProviderType.HUGGINGFACE not in gateway.adapters
    with pytest.raises(ValueError, match="incomplete"):
        build_ai_gateway(
            Settings(
                database_url="sqlite+aiosqlite://",
                huggingface_enabled=True,
                huggingface_token=SecretStr("inference-only"),
            ),
            client=client,
        )
    await client.aclose()
