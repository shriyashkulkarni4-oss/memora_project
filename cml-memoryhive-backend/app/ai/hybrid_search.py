"""Deterministic exact/keyword/semantic ranking with explainable RRF fusion."""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class SearchSignals:
    item_id: str
    lexical_score: float
    reasons: tuple[str, ...]
    snippet: str | None


@dataclass(frozen=True)
class RankedSearchMatch:
    item_id: str
    score: float
    reasons: tuple[str, ...]
    snippet: str | None
    semantic_score: float | None = None


def _snippet(text: str | None, query: str, *, radius: int = 90) -> str | None:
    if not text:
        return None
    normalized = text.casefold()
    position = normalized.find(query.casefold())
    if position < 0:
        return text[: radius * 2].strip() or None
    start = max(0, position - radius)
    end = min(len(text), position + len(query) + radius)
    value = text[start:end].strip()
    return f"{'…' if start else ''}{value}{'…' if end < len(text) else ''}"


def lexical_signals(item, query: str) -> SearchSignals:
    """Score exact product fields without using or exposing hidden model state."""
    value = query.casefold().strip()
    score = 0.0
    reasons: list[str] = []
    snippet = None
    title = (item.title or "").casefold()
    url = (item.url or "").casefold()
    domain = (item.source_domain or "").casefold()
    source = (item.source or "").casefold()
    tags = [(tag.name or "").casefold() for tag in item.tags]
    if value and value == title:
        score += 12
        reasons.append("exact")
    elif value and value in title:
        score += 8
        reasons.append("exact")
    if value and (value in url or value in domain):
        score += 7
        reasons.extend(["exact", "source"])
    if value and any(value == tag or value in tag for tag in tags):
        score += 9
        reasons.append("tag")
    if value and value in source:
        score += 5
        reasons.append("source")
    for text in (
        item.raw_text,
        item.extracted_text,
        item.summary,
        item.description,
        item.notes,
    ):
        if text and value in text.casefold():
            score += 3
            reasons.append("phrase")
            snippet = snippet or _snippet(text, query)
    created_at = item.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if (datetime.now(timezone.utc) - created_at).days <= 30:
        score += 0.25
    return SearchSignals(
        item.id,
        score,
        tuple(dict.fromkeys(reasons)),
        snippet,
    )


def reciprocal_rank_fusion(
    lexical: list[SearchSignals],
    semantic: list[tuple[str, float, str | None]],
    *,
    rrf_k: int,
    keyword_weight: float,
    semantic_weight: float,
) -> tuple[RankedSearchMatch, ...]:
    lexical = sorted(lexical, key=lambda value: (-value.lexical_score, value.item_id))
    semantic = sorted(semantic, key=lambda value: (-value[1], value[0]))
    scores: dict[str, float] = {}
    details: dict[str, tuple[list[str], str | None, float | None]] = {}
    for rank, signal in enumerate(lexical, start=1):
        scores[signal.item_id] = scores.get(signal.item_id, 0) + keyword_weight / (
            rrf_k + rank
        )
        details[signal.item_id] = (list(signal.reasons), signal.snippet, None)
    for rank, (item_id, similarity, snippet) in enumerate(semantic, start=1):
        scores[item_id] = scores.get(item_id, 0) + semantic_weight / (rrf_k + rank)
        reasons, existing_snippet, _ = details.setdefault(item_id, ([], None, None))
        reasons.append("semantic")
        details[item_id] = (reasons, existing_snippet or snippet, similarity)
    return tuple(
        RankedSearchMatch(
            item_id=item_id,
            score=score,
            reasons=tuple(dict.fromkeys(details[item_id][0])),
            snippet=details[item_id][1],
            semantic_score=details[item_id][2],
        )
        for item_id, score in sorted(
            scores.items(), key=lambda value: (-value[1], value[0])
        )
    )
