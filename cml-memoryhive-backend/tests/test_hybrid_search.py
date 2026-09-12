"""Owner-scoped hybrid API ranking, explanations, filters, and degradation."""

from dataclasses import dataclass, field

import pytest

from app.ai.contracts import EmbeddingRequest, EmbeddingResult
from app.ai.gateway import AIGateway, ProviderCapability, ProviderLimits, ProviderType
from app.config import Settings
from app.models import DocumentChunk, EmbeddingIndex, Item, ItemEmbedding
from tests.test_core_api import register_and_login

pytestmark = pytest.mark.asyncio


@dataclass
class QueryAdapter:
    provider_type: ProviderType = ProviderType.OLLAMA
    capabilities: frozenset[ProviderCapability] = frozenset(
        {ProviderCapability.EMBEDDINGS}
    )
    limits: ProviderLimits = ProviderLimits(maximum_attempts=1)
    calls: list[str] = field(default_factory=list)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.calls.append(request.text)
        return EmbeddingResult(
            request.chunk_id,
            request.model_alias,
            request.expected_dimensions,
            [1.0, 0.0, 0.0],
            self.provider_type.value,
        )


async def capture(client, headers, *, title: str, text: str, source: str = "notes"):
    response = await client.post(
        "/api/v1/items",
        headers=headers,
        json={"type": "text", "title": title, "raw_text": text, "source": source},
    )
    assert response.status_code == 201
    return response.json()


async def test_hybrid_search_fuses_exact_and_semantic_results_without_tenant_leakage(
    api_client_with_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _storage, factory = api_client_with_db
    owner, headers = await register_and_login(client, "hybrid-owner@example.com")
    other, other_headers = await register_and_login(client, "hybrid-other@example.com")
    exact = await capture(
        client,
        headers,
        title="jobs surviving restarts",
        text="An exact phrase reference.",
    )
    semantic = await capture(
        client,
        headers,
        title="Durable orchestration",
        text="Stateful execution continues safely after process failure.",
        source="research",
    )
    unrelated = await capture(
        client, headers, title="Cooking", text="A sourdough bread recipe."
    )
    foreign = await capture(
        client,
        other_headers,
        title="Private foreign memory",
        text="Never expose this content.",
    )
    async with factory() as session:
        index = EmbeddingIndex(
            provider="ollama",
            model="embed-v1",
            dimensions=3,
            normalization="l2",
            version=1,
        )
        session.add(index)
        await session.flush()
        for record, user_id, vector in (
            (exact, owner["id"], [0.0, 1.0, 0.0]),
            (semantic, owner["id"], [1.0, 0.0, 0.0]),
            (unrelated, owner["id"], [0.0, 1.0, 0.0]),
            (foreign, other["id"], [1.0, 0.0, 0.0]),
        ):
            item = await session.get(Item, record["id"])
            assert item is not None
            item.extracted_text = record["raw_text"]
            chunk = DocumentChunk(
                chunk_key=f"{record['id']}:0:semantic",
                user_id=user_id,
                item_id=record["id"],
                analysis_version=1,
                ordinal=0,
                text=record["raw_text"],
                start_offset=0,
                end_offset=len(record["raw_text"]),
                content_hash=f"hash-{record['id']}",
            )
            session.add(chunk)
            session.add(
                ItemEmbedding(
                    user_id=user_id,
                    item_id=record["id"],
                    analysis_version=1,
                    chunk_id=chunk.chunk_key,
                    index_id=index.id,
                    provider="ollama",
                    model="embed-v1",
                    dimensions=3,
                    normalization="l2",
                    index_version=1,
                    vector=vector,
                    content_hash=chunk.content_hash,
                )
            )
        await session.commit()

    adapter = QueryAdapter()
    configured = Settings(
        database_url="sqlite+aiosqlite://",
        ollama_base_url="http://localhost:11434",
        ollama_embedding_model="embed-v1",
        ai_embeddings_route="ollama:embed-v1",
        ai_embedding_dimensions=3,
        ai_search_semantic_threshold=0.5,
    )
    from app.api.v1 import items as items_api

    monkeypatch.setattr(items_api, "get_settings", lambda: configured)
    monkeypatch.setattr(
        items_api, "build_ai_gateway", lambda _settings: AIGateway([adapter])
    )

    response = await client.get(
        "/api/v1/items", params={"q": "jobs surviving restarts"}, headers=headers
    )
    assert response.status_code == 200
    results = response.json()["items"]
    assert [record["id"] for record in results] == [exact["id"], semantic["id"]]
    assert results[0]["search_match"]["reasons"] == ["exact"]
    assert "semantic" in results[1]["search_match"]["reasons"]
    assert "Stateful execution" in results[1]["search_match"]["snippet"]
    assert foreign["id"] not in {record["id"] for record in results}
    assert adapter.calls == ["jobs surviving restarts"]

    filtered = await client.get(
        "/api/v1/items",
        params={"q": "jobs surviving restarts", "source": "research"},
        headers=headers,
    )
    assert [record["id"] for record in filtered.json()["items"]] == [semantic["id"]]


async def test_search_remains_keyword_only_when_ai_is_disabled(
    api_client_with_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _storage, _factory = api_client_with_db
    _owner, headers = await register_and_login(client, "keyword-only@example.com")
    exact = await capture(
        client,
        headers,
        title="invoice ACME-1042",
        text="Exact identifiers remain searchable offline.",
    )
    from app.api.v1 import items as items_api

    monkeypatch.setattr(
        items_api,
        "get_settings",
        lambda: Settings(database_url="sqlite+aiosqlite://"),
    )
    response = await client.get(
        "/api/v1/items", params={"q": "ACME-1042"}, headers=headers
    )
    assert response.status_code == 200
    assert [record["id"] for record in response.json()["items"]] == [exact["id"]]
    assert "exact" in response.json()["items"][0]["search_match"]["reasons"]
