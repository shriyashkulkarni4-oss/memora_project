"""Restricted generic OpenAI-compatible endpoint conformance tests."""

import json

import httpx
import pytest

from app.ai.contracts import EmbeddingRequest, EnrichmentRequest
from app.ai.gateway import (
    AIGateway,
    ProviderError,
    ProviderErrorCode,
    ProviderLimits,
    ProviderType,
)
from app.ai.providers.openai_compatible import OpenAICompatibleAdapter

pytestmark = pytest.mark.asyncio


async def public_resolver(_host: str) -> tuple[str, ...]:
    return ("93.184.216.34",)


def result_json() -> str:
    return json.dumps(
        {
            "summary": "Compatible structured result.",
            "detailed_summary": None,
            "topics": [],
            "suggested_tags": [],
            "classification": "note",
            "entities": [],
            "key_phrases": [],
            "confidence": 0.7,
            "warnings": [],
        }
    )


def adapter(
    client: httpx.AsyncClient,
    *,
    host: str = "api.vendor.test",
    model: str = "vendor-chat",
    mode: str = "chat_completions",
    capabilities: list[str] | None = None,
    allow_private: bool = False,
    private_hosts: list[str] | None = None,
    resolver=public_resolver,
    extra_headers: dict[str, str] | None = None,
) -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        base_url=f"https://{host}/v1",
        api_key="compatible-secret",
        default_model=model,
        embedding_model="vendor-embed",
        endpoint_mode=mode,
        declared_capabilities=capabilities
        or ["enrichment", "embeddings", "model_listing", "health", "token_usage"],
        chat_models=[model],
        embedding_models=["vendor-embed"],
        allowed_hosts=[host],
        allow_private_network=allow_private,
        private_hosts=private_hosts or [],
        extra_headers=extra_headers,
        extra_options={"reasoning_effort": "low"},
        client=client,
        limits=ProviderLimits(maximum_attempts=1),
        resolver=resolver,
    )


@pytest.mark.parametrize(
    ("vendor", "host", "model"),
    [
        ("openai", "api.openai.test", "gpt-test"),
        ("deepseek", "api.deepseek.test", "deepseek-chat"),
        ("vllm", "vllm.internal.test", "local-model"),
        ("lm-studio", "lmstudio.internal.test", "local-model"),
    ],
)
async def test_chat_contract_is_identical_for_named_compatible_fixtures(
    vendor: str, host: str, model: str
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "id": f"{vendor}-request",
                "model": model,
                "choices": [
                    {"message": {"content": result_json()}, "finish_reason": "stop"}
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 3,
                    "total_tokens": 8,
                },
            },
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    response = await AIGateway([adapter(client, host=host, model=model)]).enrich(
        ProviderType.OPENAI_COMPATIBLE,
        EnrichmentRequest("item", 1, f"{vendor} compatible content"),
    )
    await client.aclose()

    assert response.enrichment.summary == "Compatible structured result."
    assert response.provenance.configured_model == model
    assert response.usage.total_tokens == 8
    assert seen[0].url.host == host
    assert seen[0].headers["authorization"] == "Bearer compatible-secret"
    assert json.loads(seen[0].content)["reasoning_effort"] == "low"


async def test_responses_mode_is_separately_declared_and_parsed() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "id": "response-1",
                    "model": "vendor-chat",
                    "status": "completed",
                    "output_text": result_json(),
                    "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
                },
                request=request,
            )
        )
    )
    response = await AIGateway([adapter(client, mode="responses")]).enrich(
        ProviderType.OPENAI_COMPATIBLE, EnrichmentRequest("item", 1, "content")
    )
    await client.aclose()
    assert response.enrichment.summary == "Compatible structured result."
    assert response.provenance.routing_policy["endpoint_mode"] == "responses"


async def test_embeddings_require_flag_and_stable_dimensions() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"model": "vendor-embed", "data": [{"embedding": [0.1, 0.2]}]},
                request=request,
            )
        )
    )
    gateway = AIGateway([adapter(client)])
    with pytest.raises(ProviderError) as changed:
        await gateway.embed(
            ProviderType.OPENAI_COMPATIBLE,
            EmbeddingRequest("chunk", "content", "vendor-embed", 3),
        )
    assert changed.value.code == ProviderErrorCode.MALFORMED_RESPONSE

    without_flag = AIGateway(
        [adapter(client, capabilities=["enrichment", "health", "model_listing"])]
    )
    with pytest.raises(ProviderError) as unsupported:
        await without_flag.embed(
            ProviderType.OPENAI_COMPATIBLE,
            EmbeddingRequest("chunk", "content", "vendor-embed", 2),
        )
    await client.aclose()
    assert unsupported.value.code == ProviderErrorCode.UNSUPPORTED_CAPABILITY


async def test_host_mode_header_and_extension_guards() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: None))
    with pytest.raises(ValueError, match="not allowlisted"):
        OpenAICompatibleAdapter(
            base_url="https://unapproved.test/v1",
            api_key=None,
            default_model="model",
            embedding_model=None,
            endpoint_mode="chat_completions",
            declared_capabilities=["enrichment"],
            chat_models=["model"],
            embedding_models=[],
            allowed_hosts=["approved.test"],
            client=client,
        )
    with pytest.raises(ValueError, match="endpoint mode"):
        adapter(client, mode="magic")
    with pytest.raises(ValueError, match="header"):
        adapter(client, extra_headers={"Authorization": "override"})
    await client.aclose()


@pytest.mark.parametrize(
    "host", ["127.0.0.1", "169.254.169.254", "metadata.google.internal"]
)
async def test_private_link_local_and_metadata_destinations_are_blocked(
    host: str,
) -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: None))
    with pytest.raises(ValueError):
        adapter(client, host=host)
    await client.aclose()


async def test_validated_private_host_is_explicitly_allowed() -> None:
    async def private_resolver(_host: str) -> tuple[str, ...]:
        return ("10.0.0.10",)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "model": "local-model",
                    "choices": [{"message": {"content": result_json()}}],
                },
                request=request,
            )
        )
    )
    response = await AIGateway(
        [
            adapter(
                client,
                host="vllm.internal",
                model="local-model",
                allow_private=True,
                private_hosts=["vllm.internal"],
                resolver=private_resolver,
            )
        ]
    ).enrich(ProviderType.OPENAI_COMPATIBLE, EnrichmentRequest("item", 1, "content"))
    await client.aclose()
    assert response.enrichment.summary


async def test_redirect_cannot_send_secret_to_another_host() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            307,
            headers={"location": "https://evil.test/steal"},
            request=request,
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    )
    with pytest.raises(ProviderError) as caught:
        await AIGateway([adapter(client)]).enrich(
            ProviderType.OPENAI_COMPATIBLE, EnrichmentRequest("item", 1, "content")
        )
    await client.aclose()
    assert caught.value.code == ProviderErrorCode.INVALID_REQUEST
    assert len(seen) == 1
    assert seen[0].url.host == "api.vendor.test"


async def test_non_compatible_response_is_rejected() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"answer": "not OpenAI compatible"}, request=request
            )
        )
    )
    with pytest.raises(ProviderError) as caught:
        await AIGateway([adapter(client)]).enrich(
            ProviderType.OPENAI_COMPATIBLE, EnrichmentRequest("item", 1, "content")
        )
    await client.aclose()
    assert caught.value.code == ProviderErrorCode.MALFORMED_RESPONSE
