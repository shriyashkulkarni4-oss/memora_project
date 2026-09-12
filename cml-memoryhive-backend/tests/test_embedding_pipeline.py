"""Versioned chunk persistence, vector reuse, migration, and deletion tests."""

from dataclasses import dataclass, field

import pytest
from sqlalchemy import func, select

from app.ai.contracts import EmbeddingRequest, EmbeddingResult, ExtractedDocument
from app.ai.embedding_pipeline import EmbeddingPipeline, backfill_embeddings
from app.ai.gateway import (
    AIGateway,
    ProviderCapability,
    ProviderLimits,
    ProviderType,
)
from app.config import Settings
from app.models import DocumentChunk, EmbeddingIndex, Item, ItemEmbedding
from tests.test_core_api import register_and_login

pytestmark = pytest.mark.asyncio


@dataclass
class FakeEmbeddingAdapter:
    provider_type: ProviderType = ProviderType.OLLAMA
    capabilities: frozenset[ProviderCapability] = frozenset(
        {ProviderCapability.EMBEDDINGS}
    )
    limits: ProviderLimits = ProviderLimits(maximum_attempts=1)
    calls: list[EmbeddingRequest] = field(default_factory=list)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.calls.append(request)
        vector = [1.0] + [
            float((len(request.text) + index) % 7 + 1)
            for index in range(request.expected_dimensions - 1)
        ]
        return EmbeddingResult(
            chunk_id=request.chunk_id,
            model_alias=request.model_alias,
            dimensions=request.expected_dimensions,
            vector=vector,
            provider=self.provider_type.value,
            usage={"input_tokens": max(1, len(request.text) // 4)},
        )


def settings(*, version: int = 1, dimensions: int = 3) -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite://",
        ollama_base_url="http://localhost:11434",
        ollama_embedding_model="embed-v1",
        ai_embeddings_route="ollama:embed-v1",
        ai_embedding_dimensions=dimensions,
        ai_embedding_index_version=version,
        ai_embedding_chunk_characters=24,
        ai_embedding_chunk_overlap=4,
        ai_embedding_backfill_batch_size=1,
        ai_embedding_backfill_max_items_per_minute=1,
    )


async def create_item(client, headers, text: str) -> dict[str, object]:
    response = await client.post(
        "/api/v1/items",
        headers=headers,
        json={"type": "text", "raw_text": text},
    )
    assert response.status_code == 201
    return response.json()


async def test_unchanged_chunks_are_reused_across_analysis_versions_and_deleted(
    api_client_with_db,
) -> None:
    client, _storage, session_factory = api_client_with_db
    user, headers = await register_and_login(client, "embedding-reuse@example.com")
    item = await create_item(
        client, headers, "semantic memory retrieval uses durable vector chunks"
    )
    adapter = FakeEmbeddingAdapter()
    pipeline = EmbeddingPipeline(session_factory, AIGateway([adapter]), settings())
    document = ExtractedDocument(
        item_id=item["id"], analysis_version=1, extracted_text=item["raw_text"]
    )

    first = await pipeline.embed_document(document, user_id=user["id"])
    second = await pipeline.embed_document(
        ExtractedDocument(
            item_id=item["id"], analysis_version=2, extracted_text=item["raw_text"]
        ),
        user_id=user["id"],
    )

    assert first.embedded == first.chunks > 1
    assert second.embedded == 0
    assert second.reused == second.chunks
    assert len(adapter.calls) == first.chunks
    async with session_factory() as session:
        assert (
            await session.scalar(select(func.count(DocumentChunk.id)))
            == first.chunks * 2
        )
        assert (
            await session.scalar(select(func.count(ItemEmbedding.id)))
            == first.chunks * 2
        )

    deleted = await client.delete(f"/api/v1/items/{item['id']}", headers=headers)
    assert deleted.status_code == 204
    async with session_factory() as session:
        assert await session.scalar(select(func.count(DocumentChunk.id))) == 0
        assert await session.scalar(select(func.count(ItemEmbedding.id))) == 0


async def test_schema_change_creates_parallel_index_and_cursor_backfill_resumes(
    api_client_with_db,
) -> None:
    client, _storage, session_factory = api_client_with_db
    user, headers = await register_and_login(client, "embedding-index@example.com")
    first_item = await create_item(client, headers, "first semantic document")
    second_item = await create_item(client, headers, "second semantic document")
    adapter = FakeEmbeddingAdapter()

    initial = EmbeddingPipeline(session_factory, AIGateway([adapter]), settings())
    await initial.embed_document(
        ExtractedDocument(
            item_id=first_item["id"],
            analysis_version=1,
            extracted_text=first_item["raw_text"],
        ),
        user_id=user["id"],
    )
    migrated = EmbeddingPipeline(
        session_factory, AIGateway([adapter]), settings(version=2, dimensions=4)
    )
    await migrated.embed_document(
        ExtractedDocument(
            item_id=first_item["id"],
            analysis_version=1,
            extracted_text=first_item["raw_text"],
        ),
        user_id=user["id"],
    )
    async with session_factory() as session:
        indexes = list(await session.scalars(select(EmbeddingIndex)))
    assert {(index.version, index.dimensions) for index in indexes} == {(1, 3), (2, 4)}

    async with session_factory() as session:
        for item_id, text in (
            (first_item["id"], first_item["raw_text"]),
            (second_item["id"], second_item["raw_text"]),
        ):
            value = await session.get(Item, item_id)
            assert value is not None
            value.extracted_text = text
        await session.commit()
    page_one = await backfill_embeddings(migrated)
    assert len(page_one.outcomes) == 1
    assert page_one.next_cursor is not None
    page_two = await backfill_embeddings(migrated, cursor=page_one.next_cursor)
    assert len(page_two.outcomes) == 1
    assert page_two.exhausted is True
