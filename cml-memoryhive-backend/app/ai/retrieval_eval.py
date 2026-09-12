"""Small provider-neutral retrieval metrics shared by embedding/search evaluations."""

import math
from collections.abc import Iterable, Sequence


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or len(left) != len(right):
        raise ValueError("vectors must have the same non-zero dimension")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("vectors must have non-zero norms")
    return sum(a * b for a, b in zip(left, right, strict=True)) / (
        left_norm * right_norm
    )


def rank_by_cosine(
    query: Sequence[float], candidates: Iterable[tuple[str, Sequence[float]]], *, k: int
) -> tuple[str, ...]:
    if k < 1:
        raise ValueError("k must be positive")
    scored = [
        (cosine_similarity(query, vector), identifier)
        for identifier, vector in candidates
    ]
    scored.sort(key=lambda value: (-value[0], value[1]))
    return tuple(identifier for _score, identifier in scored[:k])


def recall_at_k(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
    expected = set(relevant)
    if not expected:
        raise ValueError("at least one relevant document is required")
    return len(expected.intersection(retrieved)) / len(expected)


def ndcg_at_k(retrieved: Sequence[str], relevant: Sequence[str], *, k: int) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    expected = set(relevant)
    if not expected:
        raise ValueError("at least one relevant document is required")
    gains = [1.0 if item_id in expected else 0.0 for item_id in retrieved[:k]]
    dcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal = sum(1.0 / math.log2(rank + 2) for rank in range(min(k, len(expected))))
    return dcg / ideal
