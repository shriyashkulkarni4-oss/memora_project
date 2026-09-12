"""Committed retrieval-corpus quality and latency gates."""

import json
import time
from pathlib import Path

from app.ai.retrieval_eval import ndcg_at_k, rank_by_cosine, recall_at_k


def test_embedding_corpus_recall_at_k_and_latency() -> None:
    corpus = json.loads(
        (
            Path(__file__).parent / "fixtures" / "embedding_retrieval_corpus.json"
        ).read_text(encoding="utf-8")
    )
    candidates = [
        (document["id"], document["vector"]) for document in corpus["documents"]
    ]
    recalls: list[float] = []
    ndcgs: list[float] = []
    baseline_recalls: list[float] = []
    latencies_ms: list[float] = []
    for query in corpus["queries"]:
        started = time.perf_counter()
        retrieved = rank_by_cosine(query["vector"], candidates, k=2)
        latencies_ms.append((time.perf_counter() - started) * 1_000)
        recalls.append(recall_at_k(retrieved, query["relevant"]))
        ndcgs.append(ndcg_at_k(retrieved, query["relevant"], k=2))
        terms = set(query["text"].casefold().split())
        keyword = [
            document["id"]
            for document in corpus["documents"]
            if terms.intersection(document["text"].casefold().split())
        ][:2]
        baseline_recalls.append(recall_at_k(keyword, query["relevant"]))

    assert sum(recalls) / len(recalls) >= 0.95
    assert sum(ndcgs) / len(ndcgs) >= 0.95
    assert sum(recalls) / len(recalls) > sum(baseline_recalls) / len(baseline_recalls)
    assert max(latencies_ms) < 50
