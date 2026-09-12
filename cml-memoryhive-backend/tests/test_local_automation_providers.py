"""Hardened Ollama and n8n provider behavior."""

import hashlib
import hmac
import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.ai.contracts import EmbeddingRequest, EnrichmentRequest
from app.ai.gateway import AIGateway, ProviderError, ProviderErrorCode, ProviderType
from app.ai.providers import N8nAdapter, OllamaAdapter
from app.config import Settings

pytestmark = pytest.mark.asyncio


async def test_ollama_structured_output_keepalive_and_embeddings() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/api/generate":
            return httpx.Response(
                200,
                json={
                    "model": "local-chat",
                    "response": json.dumps(
                        {
                            "summary": "Local structured result.",
                            "topics": ["privacy"],
                            "suggested_tags": [],
                        }
                    ),
                    "prompt_eval_count": 6,
                    "eval_count": 3,
                    "done_reason": "stop",
                },
                request=request,
            )
        if request.url.path == "/api/embed":
            return httpx.Response(
                200,
                json={
                    "model": "local-embed",
                    "embeddings": [[0.1, 0.2, 0.3]],
                    "prompt_eval_count": 4,
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={"models": [{"name": "local-chat"}, {"name": "local-embed"}]},
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaAdapter(
        "http://ollama.internal:11434",
        "local-chat",
        embedding_model="local-embed",
        keep_alive="15m",
        deployment_type="self_hosted",
        client=client,
    )
    gateway = AIGateway([adapter])
    enrichment = await gateway.enrich(
        ProviderType.OLLAMA, EnrichmentRequest("item", 1, "private content")
    )
    embedding = await gateway.embed(
        ProviderType.OLLAMA,
        EmbeddingRequest("chunk", "private content", "local-embed", 3),
    )
    health = await gateway.health(ProviderType.OLLAMA)
    await client.aclose()

    assert enrichment.enrichment.summary == "Local structured result."
    assert enrichment.provenance.routing_policy["deployment_type"] == "self_hosted"
    assert embedding.vector == (0.1, 0.2, 0.3)
    assert health.available is True
    generate_body = json.loads(seen[0].content)
    assert generate_body["keep_alive"] == "15m"
    assert generate_body["format"]["type"] == "object"


async def test_ollama_model_outage_is_not_false_success() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"models": []}, request=request)
        )
    )
    health = await AIGateway(
        [OllamaAdapter("http://ollama", "missing", client=client)]
    ).health(ProviderType.OLLAMA)
    await client.aclose()
    assert health.available is False
    assert health.message == "configured Ollama model is unavailable"


async def test_n8n_contract_is_versioned_and_request_is_signed() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "schema_version": 1,
                "summary": "Automation result",
                "topics": [],
                "tags": [],
            },
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = N8nAdapter(
        "https://n8n.internal/webhook",
        signing_secret="signing-secret",
        deployment_type="self_hosted",
        client=client,
        clock=lambda: 1_789_000_000,
    )
    response = await AIGateway([adapter]).enrich(
        ProviderType.N8N,
        EnrichmentRequest("item", 3, "signed content", language="en"),
    )
    await client.aclose()

    request = seen[0]
    expected = hmac.new(
        b"signing-secret",
        b"1789000000." + request.content,
        hashlib.sha256,
    ).hexdigest()
    assert request.headers["x-memoryhive-timestamp"] == "1789000000"
    assert request.headers["x-memoryhive-signature"] == f"sha256={expected}"
    assert json.loads(request.content)["schema_version"] == 1
    assert json.loads(request.content)["analysis_version"] == 3
    assert response.provenance.routing_policy["deployment_type"] == "self_hosted"


async def test_n8n_schema_drift_is_rejected_atomically() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"schema_version": 2, "summary": "wrong contract"},
                request=request,
            )
        )
    )
    with pytest.raises(ProviderError) as caught:
        await AIGateway([N8nAdapter("https://n8n.test", client=client)]).enrich(
            ProviderType.N8N, EnrichmentRequest("item", 1, "content")
        )
    await client.aclose()
    assert caught.value.code == ProviderErrorCode.MALFORMED_RESPONSE


async def test_production_rejects_unauthenticated_external_n8n() -> None:
    base = {
        "environment": "production",
        "app_debug": False,
        "jwt_secret_key": "j" * 32,
        "encryption_key": "e" * 32,
        "database_url": "postgresql+asyncpg://secure:password@db:5432/app",
        "minio_access_key": "secure-access",
        "minio_secret_key": "secure-secret",
        "redis_url": "redis://redis:6379/0",
        "cors_origins": ["https://memoryhive.example"],
        "cors_origin_regex": None,
        "allowed_hosts": ["memoryhive.example"],
        "n8n_webhook_url": "https://automation.example/webhook",
    }
    with pytest.raises(ValidationError, match="requires N8N_API_KEY"):
        Settings(**base)

    secured = Settings(**base, n8n_signing_secret=SecretStr("signed"))
    assert secured.n8n_signing_secret
