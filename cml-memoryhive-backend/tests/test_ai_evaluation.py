"""Versioned, consent-safe AI evaluation and release-gate tests."""

import json
from pathlib import Path

import pytest

from app.ai.evaluation import evaluate_dataset, load_json, validate_live_evaluation

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "evaluations/datasets/memoryhive_ai_v1.json"
THRESHOLDS = ROOT / "evaluations/thresholds.json"
BASELINE = ROOT / "evaluations/baseline.json"


def test_offline_evaluation_passes_release_floors_without_credentials() -> None:
    report = evaluate_dataset(
        load_json(DATASET), load_json(THRESHOLDS), baseline=load_json(BASELINE)
    )
    assert report.passed
    assert report.provider == "offline-deterministic"
    assert report.redacted
    assert report.metrics["groundedness"] == 1
    assert report.metrics["citation_correctness"] == 1
    assert not report.trend_warnings


def test_quality_regression_blocks_rollout() -> None:
    dataset = load_json(DATASET)
    dataset["content_cases"][0]["actual"]["classification"] = "wrong"
    dataset["retrieval_cases"][0]["retrieved"] = ["irrelevant"]
    report = evaluate_dataset(
        dataset, load_json(THRESHOLDS), baseline=load_json(BASELINE)
    )
    assert not report.passed
    assert any("classification_accuracy" in value for value in report.blocking_failures)
    assert any("recall_at_k" in value for value in report.blocking_failures)
    assert report.trend_warnings


def test_dataset_explicitly_excludes_unapproved_production_data() -> None:
    dataset = load_json(DATASET)
    assert dataset["metadata"]["consent_basis"] == "synthetic_and_public_domain"
    assert dataset["metadata"]["contains_production_user_data"] is False
    assert {case["item_type"] for case in dataset["content_cases"]} == {
        "link",
        "screenshot",
        "text",
    }
    assert "hi" in dataset["metadata"]["languages"]
    dataset["metadata"].pop("contains_production_user_data")
    with pytest.raises(ValueError, match="exclude production"):
        evaluate_dataset(dataset, load_json(THRESHOLDS))


def test_baseline_identifies_provider_model_prompt_schema_and_dataset() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert baseline["dataset_version"] == "memoryhive-ai-v1"
    assert baseline["schema_version"] == "1"
    assert baseline["provider"]
    assert baseline["model"]
    assert baseline["prompt_version"]


def test_live_evaluations_require_opt_in_and_a_hard_cost_cap() -> None:
    with pytest.raises(ValueError, match="explicit opt-in"):
        validate_live_evaluation(opted_in=False, maximum_cost_usd=0.01)
    with pytest.raises(ValueError, match="cost cap"):
        validate_live_evaluation(opted_in=True, maximum_cost_usd=0.051)
    validate_live_evaluation(opted_in=True, maximum_cost_usd=0.05)
