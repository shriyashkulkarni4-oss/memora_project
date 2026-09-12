"""Versioned, resumable document chunking and embedding persistence."""

import math
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.budgets import DatabaseBudgetGuard
from app.ai.contracts import (
    ContentChunk,
    EmbeddingRequest,
    ExtractedDocument,
    chunk_document,
)
from app.ai.gateway import (
    AIGateway,
    ProviderError,
    ProviderErrorCode,
    ProviderType,
    ProviderUsage,
)
from app.ai.policy import AITask, resolve_task_policy
from app.config import Settings, get_settings
from app.models import DocumentChunk, EmbeddingIndex, Item, ItemEmbedding, User
from app.observability import (
    AI_CALLS,
    AI_COST,
    AI_LATENCY,
    AI_TOKENS,
    configured_model_alias,
)


@dataclass(frozen=True)
class EmbeddingOutcome:
    item_id: str
    analysis_version: int
    index_id: str | None
    chunks: int
    embedded: int
    reused: int
    status: str


@dataclass(frozen=True)
class EmbeddingBackfillPage:
    outcomes: tuple[EmbeddingOutcome, ...]
    next_cursor: str | None
    exhausted: bool


@dataclass(frozen=True)
class QueryEmbedding:
    index_id: str
    provider: ProviderType
    model: str
    vector: tuple[float, ...]


def normalize_vector(vector: tuple[float, ...], mode: str) -> list[float]:
    if mode == "none":
        return list(vector)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise ValueError("embedding vector cannot have zero norm")
    return [value / norm for value in vector]


class EmbeddingPipeline:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        gateway: AIGateway,
        settings: Settings | None = None,
        budget_guard: DatabaseBudgetGuard | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.gateway = gateway
        self.settings = settings or get_settings()
        self.budget_guard = budget_guard

    async def embed_document(
        self, document: ExtractedDocument, *, user_id: str
    ) -> EmbeddingOutcome:
        if not self.settings.ai_embeddings_enabled:
            return EmbeddingOutcome(
                document.item_id, document.analysis_version, None, 0, 0, 0, "disabled"
            )
        chunks = chunk_document(
            document,
            maximum_characters=self.settings.ai_embedding_chunk_characters,
            overlap=self.settings.ai_embedding_chunk_overlap,
        )
        if not chunks:
            return EmbeddingOutcome(
                document.item_id, document.analysis_version, None, 0, 0, 0, "empty"
            )
        policy = resolve_task_policy(
            self.settings,
            self.gateway,
            AITask.EMBEDDINGS,
            external_allowed_for_user=await self._external_allowed(user_id),
        )
        routes = ([policy.primary] if policy.primary else []) + list(policy.fallbacks)
        if not routes:
            await self._persist_chunks(chunks, user_id)
            return EmbeddingOutcome(
                document.item_id,
                document.analysis_version,
                None,
                len(chunks),
                0,
                0,
                "unavailable",
            )

        last_error: ProviderError | None = None
        for route in routes:
            if route is None or route.model is None:
                continue
            try:
                return await self._embed_route(
                    document, chunks, user_id, route.provider, route.model
                )
            except ProviderError as exc:
                last_error = exc
        if last_error:
            raise last_error
        return EmbeddingOutcome(
            document.item_id,
            document.analysis_version,
            None,
            len(chunks),
            0,
            0,
            "unavailable",
        )

    async def embed_query(self, text: str, *, user_id: str) -> QueryEmbedding:
        """Embed a search query without persisting its private text or vector."""
        if not self.settings.ai_embeddings_enabled:
            raise ProviderError(
                ProviderErrorCode.UNSUPPORTED_CAPABILITY,
                ProviderType.OLLAMA,
            )
        value = " ".join(text.split())
        if not value:
            raise ValueError("search query cannot be empty")
        policy = resolve_task_policy(
            self.settings,
            self.gateway,
            AITask.EMBEDDINGS,
            external_allowed_for_user=await self._external_allowed(user_id),
        )
        routes = ([policy.primary] if policy.primary else []) + list(policy.fallbacks)
        last_error: ProviderError | None = None
        for route in routes:
            if route is None or route.model is None:
                continue
            reservation = None
            labels = (
                route.provider.value,
                configured_model_alias(
                    self.settings, route.provider.value, route.model
                ),
                AITask.EMBEDDINGS.value,
            )
            try:
                async with self.session_factory() as session:
                    index = await self._index(session, route.provider, route.model)
                    await session.commit()
                if self.budget_guard:
                    reservation = await self.budget_guard.reserve(
                        operation_key=f"search-embedding:{uuid.uuid4()}",
                        user_id=user_id,
                        item_id=None,
                        task=AITask.EMBEDDINGS.value,
                        provider=route.provider,
                        model=route.model,
                        estimated_tokens=max(1, len(value) // 4),
                    )
                started = time.perf_counter()
                result = await self.gateway.embed(
                    route.provider,
                    EmbeddingRequest(
                        chunk_id=f"query:{uuid.uuid4()}",
                        text=value,
                        model_alias=route.model,
                        expected_dimensions=index.dimensions,
                    ),
                )
                vector = tuple(
                    normalize_vector(tuple(result.vector), index.normalization)
                )
                usage = ProviderUsage(
                    input_tokens=int(result.usage.get("input_tokens") or 0),
                    total_tokens=int(result.usage.get("total_tokens") or 0),
                    estimated_cost_usd=float(
                        result.usage.get("estimated_cost_usd") or 0
                    ),
                )
                if reservation and self.budget_guard:
                    await self.budget_guard.complete(reservation, usage)
                AI_CALLS.labels(*labels, "success").inc()
                AI_LATENCY.labels(*labels, "success").observe(
                    time.perf_counter() - started
                )
                AI_TOKENS.labels(*labels, "input").inc(usage.input_tokens or 0)
                AI_COST.labels(*labels).inc(usage.estimated_cost_usd or 0)
                return QueryEmbedding(index.id, route.provider, route.model, vector)
            except ProviderError as exc:
                last_error = exc
                if reservation and self.budget_guard:
                    await self.budget_guard.complete(
                        reservation, ProviderUsage(), failed=True
                    )
                AI_CALLS.labels(*labels, "failed").inc()
        if last_error:
            raise last_error
        raise ProviderError(
            ProviderErrorCode.UNSUPPORTED_CAPABILITY, ProviderType.OLLAMA
        )

    async def _external_allowed(self, user_id: str) -> bool:
        async with self.session_factory() as session:
            return bool(
                await session.scalar(
                    select(User.ai_external_processing_allowed).where(
                        User.id == user_id
                    )
                )
            )

    async def _persist_chunks(
        self, chunks: tuple[ContentChunk, ...], user_id: str
    ) -> None:
        async with self.session_factory() as session:
            for chunk in chunks:
                existing = await session.scalar(
                    select(DocumentChunk.id).where(
                        DocumentChunk.item_id == chunk.item_id,
                        DocumentChunk.analysis_version == chunk.analysis_version,
                        DocumentChunk.ordinal == chunk.ordinal,
                    )
                )
                if existing:
                    continue
                session.add(
                    DocumentChunk(
                        chunk_key=chunk.chunk_id,
                        user_id=user_id,
                        item_id=chunk.item_id,
                        analysis_version=chunk.analysis_version,
                        ordinal=chunk.ordinal,
                        text=chunk.text,
                        start_offset=chunk.start_offset,
                        end_offset=chunk.end_offset,
                        content_hash=chunk.content_hash,
                    )
                )
            await session.commit()

    async def _index(
        self, session: AsyncSession, provider: ProviderType, model: str
    ) -> EmbeddingIndex:
        index = await session.scalar(
            select(EmbeddingIndex).where(
                EmbeddingIndex.provider == provider.value,
                EmbeddingIndex.model == model,
                EmbeddingIndex.dimensions == self.settings.ai_embedding_dimensions,
                EmbeddingIndex.normalization
                == self.settings.ai_embedding_normalization,
                EmbeddingIndex.version == self.settings.ai_embedding_index_version,
            )
        )
        if index:
            return index
        index = EmbeddingIndex(
            provider=provider.value,
            model=model,
            dimensions=self.settings.ai_embedding_dimensions,
            normalization=self.settings.ai_embedding_normalization,
            version=self.settings.ai_embedding_index_version,
            status="active",
        )
        session.add(index)
        await session.flush()
        return index

    async def _embed_route(
        self,
        document: ExtractedDocument,
        chunks: tuple[ContentChunk, ...],
        user_id: str,
        provider: ProviderType,
        model: str,
    ) -> EmbeddingOutcome:
        await self._persist_chunks(chunks, user_id)
        embedded = 0
        reused = 0
        async with self.session_factory() as session:
            index = await self._index(session, provider, model)
            for chunk in chunks:
                bound = await session.scalar(
                    select(ItemEmbedding.id).where(
                        ItemEmbedding.item_id == document.item_id,
                        ItemEmbedding.analysis_version == document.analysis_version,
                        ItemEmbedding.chunk_id == chunk.chunk_id,
                        ItemEmbedding.index_id == index.id,
                    )
                )
                if bound:
                    reused += 1
                    continue
                prior = await session.scalar(
                    select(ItemEmbedding).where(
                        ItemEmbedding.user_id == user_id,
                        ItemEmbedding.index_id == index.id,
                        ItemEmbedding.content_hash == chunk.content_hash,
                    )
                )
                if prior:
                    vector = list(prior.vector)
                    reused += 1
                else:
                    reservation = None
                    if self.budget_guard:
                        reservation = await self.budget_guard.reserve(
                            operation_key=f"embedding:{index.id}:{chunk.content_hash}",
                            user_id=user_id,
                            item_id=document.item_id,
                            task=AITask.EMBEDDINGS.value,
                            provider=provider,
                            model=model,
                            estimated_tokens=max(1, len(chunk.text) // 4),
                        )
                    started = time.perf_counter()
                    alias = configured_model_alias(self.settings, provider.value, model)
                    labels = (provider.value, alias, AITask.EMBEDDINGS.value)
                    try:
                        result = await self.gateway.embed(
                            provider,
                            EmbeddingRequest(
                                chunk_id=chunk.chunk_id,
                                text=chunk.text,
                                model_alias=model,
                                expected_dimensions=index.dimensions,
                            ),
                        )
                    except ProviderError:
                        if reservation and self.budget_guard:
                            await self.budget_guard.complete(
                                reservation, ProviderUsage(), failed=True
                            )
                        AI_CALLS.labels(*labels, "failed").inc()
                        AI_LATENCY.labels(*labels, "failed").observe(
                            time.perf_counter() - started
                        )
                        raise
                    vector = normalize_vector(tuple(result.vector), index.normalization)
                    usage = ProviderUsage(
                        input_tokens=int(result.usage.get("input_tokens") or 0),
                        total_tokens=int(result.usage.get("total_tokens") or 0),
                        estimated_cost_usd=float(
                            result.usage.get("estimated_cost_usd") or 0
                        ),
                    )
                    if reservation and self.budget_guard:
                        await self.budget_guard.complete(reservation, usage)
                    AI_CALLS.labels(*labels, "success").inc()
                    AI_LATENCY.labels(*labels, "success").observe(
                        time.perf_counter() - started
                    )
                    AI_TOKENS.labels(*labels, "input").inc(usage.input_tokens or 0)
                    AI_COST.labels(*labels).inc(usage.estimated_cost_usd or 0)
                    embedded += 1
                session.add(
                    ItemEmbedding(
                        user_id=user_id,
                        item_id=document.item_id,
                        analysis_version=document.analysis_version,
                        chunk_id=chunk.chunk_id,
                        index_id=index.id,
                        provider=provider.value,
                        model=model,
                        dimensions=index.dimensions,
                        normalization=index.normalization,
                        index_version=index.version,
                        vector=vector,
                        content_hash=chunk.content_hash,
                    )
                )
            await session.commit()
            return EmbeddingOutcome(
                document.item_id,
                document.analysis_version,
                index.id,
                len(chunks),
                embedded,
                reused,
                "completed",
            )


async def backfill_embeddings(
    pipeline: EmbeddingPipeline,
    *,
    cursor: str | None = None,
    limit: int | None = None,
) -> EmbeddingBackfillPage:
    """Process one bounded page; persist the returned cursor in the caller/workflow."""
    if not pipeline.settings.ai_embedding_backfill_enabled:
        return EmbeddingBackfillPage(outcomes=(), next_cursor=cursor, exhausted=True)
    batch = min(
        limit or pipeline.settings.ai_embedding_backfill_batch_size,
        pipeline.settings.ai_embedding_backfill_max_items_per_minute,
    )
    async with pipeline.session_factory() as session:
        query = select(Item).where(
            Item.deleted_at.is_(None),
            Item.extracted_text.is_not(None),
        )
        if cursor:
            query = query.where(Item.id > cursor)
        items = list(await session.scalars(query.order_by(Item.id).limit(batch + 1)))
    page_items = items[:batch]
    outcomes: list[EmbeddingOutcome] = []
    for item in page_items:
        outcomes.append(
            await pipeline.embed_document(
                ExtractedDocument(
                    item_id=item.id,
                    analysis_version=item.analysis_version,
                    extracted_text=item.extracted_text,
                    normalized_text=item.normalized_text,
                    language=item.language,
                ),
                user_id=item.user_id,
            )
        )
    exhausted = len(items) <= batch
    return EmbeddingBackfillPage(
        outcomes=tuple(outcomes),
        next_cursor=None if exhausted or not page_items else page_items[-1].id,
        exhausted=exhausted,
    )
