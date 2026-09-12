"""Deterministic, versioned AI quality metrics and release gates."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.ai.grounded_recall import RecallPassage, verify_claims
from app.ai.retrieval_eval import ndcg_at_k, recall_at_k


@dataclass(frozen=True)
class EvaluationReport:
    dataset_version: str
    schema_version: str
    provider: str
    model: str
    prompt_version: str
    generated_at: str
    metrics: dict[str, float]
    thresholds: dict[str, dict[str, float]]
    blocking_failures: tuple[str, ...]
    trend_warnings: tuple[str, ...]
    live: bool = False
    redacted: bool = True

    @property
    def passed(self) -> bool:
        return not self.blocking_failures

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "passed": self.passed}


def _tokens(value: str) -> list[str]:
    return [
        token.casefold().strip(".,:;!?()[]{}\"'")
        for token in value.split()
        if token.strip(".,:;!?()[]{}\"'")
    ]


def token_f1(reference: str, hypothesis: str) -> float:
    expected, actual = set(_tokens(reference)), set(_tokens(hypothesis))
    if not expected:
        return 1.0 if not actual else 0.0
    precision = len(expected & actual) / len(actual) if actual else 0.0
    recall = len(expected & actual) / len(expected)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    expected = set(relevant)
    return next(
        (1 / rank for rank, value in enumerate(retrieved, 1) if value in expected), 0.0
    )


def set_precision_recall(expected: list[str], actual: list[str]) -> tuple[float, float]:
    target, predicted = {value.casefold() for value in expected}, {
        value.casefold() for value in actual
    }
    precision = (
        len(target & predicted) / len(predicted) if predicted else float(not target)
    )
    recall = len(target & predicted) / len(target) if target else float(not predicted)
    return precision, recall


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def validate_live_evaluation(*, opted_in: bool, maximum_cost_usd: float) -> None:
    if not opted_in:
        raise ValueError("live evaluations require explicit opt-in")
    if maximum_cost_usd <= 0 or maximum_cost_usd > 0.05:
        raise ValueError("live evaluation cost cap must be between 0 and 0.05 USD")


def evaluate_dataset(
    dataset: dict[str, Any],
    thresholds: dict[str, Any],
    *,
    baseline: dict[str, Any] | None = None,
) -> EvaluationReport:
    metadata = dataset["metadata"]
    if metadata.get("contains_production_user_data") is not False:
        raise ValueError(
            "evaluation dataset must explicitly exclude production user data"
        )
    extraction, ocr, summary, tag_p, tag_r, classification = [], [], [], [], [], []
    topic_f1, entity_f1, key_phrase_f1 = [], [], []
    schema = []
    for case in dataset["content_cases"]:
        expected, actual = case["expected"], case["actual"]
        extraction.append(
            _mean(
                [
                    float(actual["extraction"].get(key) == value)
                    for key, value in expected["extraction"].items()
                ]
            )
        )
        ocr.append(token_f1(expected["ocr_text"], actual["ocr_text"]))
        summary.append(token_f1(expected["summary"], actual["summary"]))
        precision, recall = set_precision_recall(expected["tags"], actual["tags"])
        tag_p.append(precision)
        tag_r.append(recall)
        classification.append(
            float(expected["classification"] == actual["classification"])
        )
        for destination, field in (
            (topic_f1, "topics"),
            (entity_f1, "entities"),
            (key_phrase_f1, "key_phrases"),
        ):
            precision, recall = set_precision_recall(expected[field], actual[field])
            destination.append(
                2 * precision * recall / (precision + recall)
                if precision + recall
                else 0.0
            )
        schema.append(
            float(
                set(actual)
                >= {
                    "extraction",
                    "ocr_text",
                    "summary",
                    "tags",
                    "classification",
                    "topics",
                    "entities",
                    "key_phrases",
                }
            )
        )

    recalls, mrrs, ndcgs, related = [], [], [], []
    for case in dataset["retrieval_cases"]:
        recalls.append(recall_at_k(case["retrieved"], case["relevant"]))
        mrrs.append(reciprocal_rank(case["retrieved"], case["relevant"]))
        ndcgs.append(ndcg_at_k(case["retrieved"], case["relevant"], k=case["k"]))
        related.append(recall_at_k(case["related"], case["related_relevant"]))

    grounded, citation_correct = [], []
    for case in dataset["grounded_answer_cases"]:
        passages = tuple(
            RecallPassage(
                index + 1, value["item_id"], value.get("title"), value["text"]
            )
            for index, value in enumerate(case["passages"])
        )
        verified = verify_claims(
            case["answer"], passages, minimum_overlap=case["minimum_overlap"]
        )
        grounded.append(float(bool(verified) == case["supported"]))
        cited = {citation for claim in verified for citation in claim.citation_ids}
        citation_correct.append(float(cited == set(case["expected_citation_ids"])))

    operations = dataset["operation_samples"]
    metrics = {
        "schema_validity": _mean(schema),
        "extraction_accuracy": _mean(extraction),
        "ocr_token_f1": _mean(ocr),
        "summary_faithfulness": _mean(summary),
        "tag_precision": _mean(tag_p),
        "tag_recall": _mean(tag_r),
        "classification_accuracy": _mean(classification),
        "topic_f1": _mean(topic_f1),
        "entity_f1": _mean(entity_f1),
        "key_phrase_f1": _mean(key_phrase_f1),
        "recall_at_k": _mean(recalls),
        "mrr": _mean(mrrs),
        "ndcg_at_k": _mean(ndcgs),
        "related_recall_at_k": _mean(related),
        "groundedness": _mean(grounded),
        "citation_correctness": _mean(citation_correct),
        "latency_p95_ms": sorted(float(value["latency_ms"]) for value in operations)[
            max(0, math.ceil(len(operations) * 0.95) - 1)
        ],
        "fallback_rate": _mean([float(value["fallback"]) for value in operations]),
        "estimated_cost_usd": sum(
            float(value["estimated_cost_usd"]) for value in operations
        ),
    }
    failures = []
    for name, rule in thresholds["release_blocking"].items():
        value = metrics[name]
        if "min" in rule and value < rule["min"]:
            failures.append(f"{name}={value:.4f} is below {rule['min']:.4f}")
        if "max" in rule and value > rule["max"]:
            failures.append(f"{name}={value:.4f} exceeds {rule['max']:.4f}")
    warnings = []
    if baseline:
        tolerance = float(thresholds.get("trend_warning_relative_drop", 0.05))
        for name, old in baseline["metrics"].items():
            if name in metrics and old > 0 and metrics[name] < old * (1 - tolerance):
                warnings.append(f"{name} dropped from {old:.4f} to {metrics[name]:.4f}")
    return EvaluationReport(
        dataset_version=metadata["version"],
        schema_version=metadata["schema_version"],
        provider=metadata.get("provider", "offline-deterministic"),
        model=metadata.get("model", "fixture-v1"),
        prompt_version=metadata["prompt_version"],
        generated_at=datetime.now(timezone.utc).isoformat(),
        metrics=metrics,
        thresholds=thresholds["release_blocking"],
        blocking_failures=tuple(failures),
        trend_warnings=tuple(warnings),
    )


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("evaluation artifact must be a JSON object")
    return value
