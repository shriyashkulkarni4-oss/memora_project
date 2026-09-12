"""Deterministic private-memory similarity, duplicate, and resurfacing ranking."""

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.retrieval_eval import cosine_similarity
from app.config import Settings
from app.models import EmbeddingIndex, Item, ItemEmbedding, ItemInteraction


@dataclass(frozen=True)
class MemoryMatch:
    item: Item
    score: float
    reasons: tuple[str, ...]
    semantic_score: float | None = None
    duplicate_kind: str | None = None


def _concepts(item: Item) -> set[str]:
    enrichment = (item.item_metadata or {}).get("enrichment")
    generated = enrichment if isinstance(enrichment, dict) else {}
    values = [tag.name.casefold() for tag in item.tags]
    for name in ("topics", "entities", "key_phrases"):
        terms = generated.get(name, [])
        if isinstance(terms, list):
            values.extend(str(value).casefold() for value in terms)
    return {value for value in values if value}


def _content_hash(item: Item) -> str | None:
    text = item.normalized_text or item.extracted_text or item.raw_text
    if not text:
        return None
    normalized = " ".join(text.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _active_model(settings: Settings) -> tuple[str, str] | None:
    route = settings.ai_embeddings_route
    if not route:
        return None
    provider, separator, model = route.partition(":")
    if separator and model:
        return provider, model
    defaults = {
        "ollama": settings.ollama_embedding_model,
        "openrouter": settings.openrouter_embedding_model,
        "huggingface": settings.huggingface_embedding_model,
        "openai_compatible": settings.openai_compatible_embedding_model,
    }
    selected = defaults.get(provider)
    return (provider, selected) if selected else None


async def semantic_scores(
    db: AsyncSession, *, user_id: str, source: Item, settings: Settings
) -> dict[str, float]:
    identity = _active_model(settings)
    if not identity:
        return {}
    provider, model = identity
    index = await db.scalar(
        select(EmbeddingIndex).where(
            EmbeddingIndex.provider == provider,
            EmbeddingIndex.model == model,
            EmbeddingIndex.dimensions == settings.ai_embedding_dimensions,
            EmbeddingIndex.normalization == settings.ai_embedding_normalization,
            EmbeddingIndex.version == settings.ai_embedding_index_version,
        )
    )
    if index is None:
        return {}
    vectors = list(
        await db.scalars(
            select(ItemEmbedding).where(
                ItemEmbedding.user_id == user_id,
                ItemEmbedding.index_id == index.id,
            )
        )
    )
    source_vectors = [
        vector.vector
        for vector in vectors
        if vector.item_id == source.id
        and vector.analysis_version == source.analysis_version
    ]
    if not source_vectors:
        return {}
    scores: dict[str, float] = {}
    for vector in vectors:
        if vector.item_id == source.id:
            continue
        similarity = max(
            cosine_similarity(source_vector, vector.vector)
            for source_vector in source_vectors
        )
        scores[vector.item_id] = max(scores.get(vector.item_id, -1), similarity)
    return scores


def rank_related(
    source: Item,
    candidates: list[Item],
    semantic: dict[str, float],
    *,
    limit: int,
) -> list[MemoryMatch]:
    source_concepts = _concepts(source)
    matches: list[MemoryMatch] = []
    for candidate in candidates:
        reasons: list[str] = []
        score = 0.0
        similarity = semantic.get(candidate.id)
        if similarity is not None and similarity >= 0.25:
            score += similarity * 5
            reasons.append("semantically similar content")
        overlap = source_concepts.intersection(_concepts(candidate))
        if overlap:
            score += min(3.0, len(overlap) * 1.25)
            reasons.append(f"shared concepts: {', '.join(sorted(overlap)[:3])}")
        if source.source_domain and source.source_domain == candidate.source_domain:
            score += 1.5
            reasons.append(f"same source: {source.source_domain}")
        elif source.source and source.source == candidate.source:
            score += 1
            reasons.append(f"same source: {source.source}")
        if score > 0:
            matches.append(MemoryMatch(candidate, score, tuple(reasons), similarity))
    matches.sort(key=lambda value: (-value.score, value.item.id))
    return matches[:limit]


def detect_duplicates(
    source: Item,
    candidates: list[Item],
    semantic: dict[str, float],
    *,
    threshold: float,
    limit: int,
) -> list[MemoryMatch]:
    source_hash = _content_hash(source)
    matches: list[MemoryMatch] = []
    for candidate in candidates:
        kind = None
        score = 0.0
        reason = ""
        if source.normalized_url and source.normalized_url == candidate.normalized_url:
            kind, score, reason = "exact_url", 1.0, "same normalized URL"
        elif {asset.sha256 for asset in source.assets if asset.sha256}.intersection(
            asset.sha256 for asset in candidate.assets if asset.sha256
        ):
            kind, score, reason = "exact_content", 1.0, "same uploaded content"
        elif source_hash and source_hash == _content_hash(candidate):
            kind, score, reason = "exact_content", 1.0, "same normalized content"
        elif semantic.get(candidate.id, -1) >= threshold:
            kind = "near_semantic"
            score = semantic[candidate.id]
            reason = "high semantic similarity"
        if kind:
            matches.append(
                MemoryMatch(
                    candidate,
                    score,
                    (reason,),
                    semantic.get(candidate.id),
                    kind,
                )
            )
    matches.sort(key=lambda value: (-value.score, value.item.id))
    return matches[:limit]


def rank_resurfacing(
    candidates: list[Item],
    interactions: list[ItemInteraction],
    *,
    now: datetime,
    limit: int,
    frequency_window_days: int,
    frequency_cap: int,
    minimum_interval_hours: int,
    max_per_source: int,
    max_per_topic: int,
) -> list[MemoryMatch]:
    reversed_ids = {
        event.reverses_id
        for event in interactions
        if event.action == "undo" and event.reverses_id
    }
    active = [event for event in interactions if event.id not in reversed_ids]
    dismissed = {event.subject_item_id for event in active if event.action == "dismiss"}
    pinned = {event.subject_item_id for event in active if event.action == "pin"}
    useful = Counter(
        event.subject_item_id for event in active if event.action == "useful"
    )
    shown_by_item: dict[str, list[datetime]] = {}
    for event in active:
        if event.action != "shown":
            continue
        created_at = event.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        shown_by_item.setdefault(event.subject_item_id, []).append(created_at)

    concept_frequency = Counter(
        concept for item in candidates[:10] for concept in _concepts(item)
    )
    ranked: list[MemoryMatch] = []
    for item in candidates:
        if item.id in dismissed:
            continue
        exposures = shown_by_item.get(item.id, [])
        recent = [
            value
            for value in exposures
            if (now - value).total_seconds() <= frequency_window_days * 86_400
        ]
        if item.id not in pinned and (
            len(recent) >= frequency_cap
            or any(
                (now - value).total_seconds() < minimum_interval_hours * 3_600
                for value in recent
            )
        ):
            continue
        created_at = item.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = max(0, (now - created_at).days)
        score = min(4.0, age_days / 30) + (2 if item.is_favorite else 0)
        reasons = [f"saved {age_days} days ago"]
        if item.id in pinned:
            score += 10
            reasons.insert(0, "pinned for resurfacing")
        if useful[item.id]:
            score += min(4, useful[item.id] * 2)
            reasons.append("previously marked useful")
        concepts = _concepts(item)
        common = sorted(concepts, key=lambda value: (-concept_frequency[value], value))
        if common and concept_frequency[common[0]] > 1:
            score += 1
            reasons.append(f"connects to your interest in {common[0]}")
        ranked.append(MemoryMatch(item, score, tuple(reasons)))
    ranked.sort(key=lambda value: (-value.score, value.item.id))

    selected: list[MemoryMatch] = []
    sources: Counter[str] = Counter()
    topics: Counter[str] = Counter()
    for match in ranked:
        source_key = match.item.source_domain or match.item.source or "personal"
        topic = sorted(_concepts(match.item))[0] if _concepts(match.item) else "other"
        if sources[source_key] >= max_per_source or topics[topic] >= max_per_topic:
            continue
        selected.append(match)
        sources[source_key] += 1
        topics[topic] += 1
        if len(selected) == limit:
            break
    return selected
