#!/usr/bin/env python3
"""Fail CI when the AI rollout contract loses a control or safe baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "ops" / "ai-rollout-policy.json"

REQUIRED_FLAGS = {
    "TEMPORAL_ENABLED",
    "OLLAMA_ENABLED",
    "N8N_ENABLED",
    "OPENROUTER_ENABLED",
    "HUGGINGFACE_ENABLED",
    "OPENAI_COMPATIBLE_ENABLED",
    "AI_STRUCTURED_ENRICHMENT_ENABLED",
    "AI_EMBEDDINGS_ENABLED",
    "AI_SEARCH_SHADOW_ENABLED",
    "AI_HYBRID_SEARCH_ENABLED",
    "AI_SUGGESTIONS_ENABLED",
    "AI_RELATED_ITEMS_ENABLED",
    "AI_RESURFACING_ENABLED",
    "AI_GROUNDED_RECALL_ENABLED",
    "AI_EMBEDDING_BACKFILL_ENABLED",
}
EXTERNAL_PROVIDERS = {
    "N8N_ENABLED",
    "OPENROUTER_ENABLED",
    "HUGGINGFACE_ENABLED",
    "OPENAI_COMPATIBLE_ENABLED",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence", type=Path, help="Validate a staging release evidence record"
    )
    args = parser.parse_args()
    policy = json.loads(POLICY.read_text())
    flags = set(policy["feature_flags"])
    missing = REQUIRED_FLAGS - flags
    if missing:
        raise SystemExit(f"rollout policy is missing flags: {sorted(missing)}")
    baseline = policy["production_baseline"]
    if set(baseline) != flags:
        raise SystemExit("production baseline must assign every feature flag exactly once")
    enabled_external = [name for name in EXTERNAL_PROVIDERS if baseline[name]]
    if enabled_external:
        raise SystemExit(f"external providers default on: {enabled_external}")
    if baseline["AI_HYBRID_SEARCH_ENABLED"]:
        raise SystemExit("hybrid ranking must remain off during the shadow baseline")
    if not baseline["AI_SEARCH_SHADOW_ENABLED"]:
        raise SystemExit("shadow evaluation must precede user-visible hybrid ranking")
    backfill = policy["backfill"]
    if not 1 <= backfill["concurrency"] <= 4:
        raise SystemExit("backfill concurrency must stay between 1 and 4")
    if not 1 <= backfill["max_items_per_minute"] <= 120:
        raise SystemExit("backfill rate must stay between 1 and 120 items/minute")
    if backfill["monthly_cost_budget_usd"] <= 0:
        raise SystemExit("backfill requires a positive explicit cost ceiling")
    if not all(policy["owners"].values()):
        raise SystemExit("every operational ownership role must be assigned")
    if len(policy["required_staging_gates"]) < 8:
        raise SystemExit("staging go/no-go gates are incomplete")
    scenarios = policy["validation_scenarios"]
    if len(scenarios) < 7 or any(set(case["enabled"]) - flags for case in scenarios):
        raise SystemExit("feature validation scenarios are incomplete or contain unknown flags")
    required_scenarios = {
        "deterministic-only",
        "temporal-local-enrichment",
        "embedding-shadow",
        "evaluated-hybrid",
        "external-provider-opt-in",
        "bounded-backfill",
        "all-user-features-local",
    }
    if {case["name"] for case in scenarios} != required_scenarios:
        raise SystemExit("feature validation scenario names do not match the contract")
    if args.evidence:
        evidence = json.loads(args.evidence.read_text())
        gate_names = set(policy["required_staging_gates"])
        recorded = {gate["name"]: gate for gate in evidence.get("gates", [])}
        if set(recorded) != gate_names:
            raise SystemExit("release evidence must contain every required staging gate")
        failed = [name for name, gate in recorded.items() if gate.get("status") != "passed"]
        if failed:
            raise SystemExit(f"release remains no-go; incomplete gates: {sorted(failed)}")
        approval = evidence.get("approval", {})
        if approval.get("decision") != "go" or not approval.get("approved_by"):
            raise SystemExit("release evidence requires an explicit named go approval")
        print(f"AI release evidence: GO ({approval['approved_by']})")
    print("AI rollout policy: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
