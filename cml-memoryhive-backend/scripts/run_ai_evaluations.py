#!/usr/bin/env python3
"""Run deterministic release gates and opt-in synthetic live provider probes."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

from app.ai.contracts import EnrichmentRequest
from app.ai.evaluation import evaluate_dataset, load_json, validate_live_evaluation
from app.ai.factory import build_ai_gateway
from app.ai.gateway import ProviderType
from app.config import get_settings

ROOT = Path(__file__).resolve().parents[1]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "evaluations/datasets/memoryhive_ai_v1.json",
    )
    parser.add_argument(
        "--thresholds", type=Path, default=ROOT / "evaluations/thresholds.json"
    )
    parser.add_argument(
        "--baseline", type=Path, default=ROOT / "evaluations/baseline.json"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--live-provider", choices=[value.value for value in ProviderType]
    )
    parser.add_argument("--live-model")
    parser.add_argument("--max-live-cost-usd", type=float, default=0.05)
    return parser.parse_args()


async def live_probe(
    provider: ProviderType, model: str | None, maximum_cost: float
) -> dict[str, object]:
    validate_live_evaluation(
        opted_in=os.environ.get("AI_LIVE_EVALUATIONS") == "true",
        maximum_cost_usd=maximum_cost,
    )
    gateway = build_ai_gateway(get_settings())
    response = await gateway.enrich(
        provider,
        EnrichmentRequest(
            item_id=f"synthetic-eval:{uuid.uuid4()}",
            analysis_version=1,
            text="Synthetic fixture: durable workflows preserve event history.",
            max_characters=1000,
        ),
        model=model,
    )
    cost = response.usage.estimated_cost_usd or 0.0
    if cost > maximum_cost:
        raise ValueError("live evaluation exceeded its cost cap")
    return {
        "provider": provider.value,
        "model": response.provenance.model or model or "provider-default",
        "latency_ms": response.provenance.latency_ms or 0,
        "estimated_cost_usd": cost,
        "schema_valid": bool(response.enrichment.summary),
        "redacted": True,
    }


async def main() -> int:
    args = arguments()
    dataset = load_json(args.dataset)
    thresholds = load_json(args.thresholds)
    baseline = load_json(args.baseline) if args.baseline.exists() else None
    report = evaluate_dataset(dataset, thresholds, baseline=baseline)
    payload = report.to_dict()
    if args.live_provider:
        probe = await live_probe(
            ProviderType(args.live_provider), args.live_model, args.max_live_cost_usd
        )
        payload["live_probe"] = probe
        payload["provider"] = probe["provider"]
        payload["model"] = probe["model"]
        payload["live"] = True
    output = (
        args.output
        or ROOT
        / "evaluation-results"
        / f"{report.dataset_version}-{payload['provider']}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "passed": report.passed,
                "output": str(output),
                "blocking_failures": report.blocking_failures,
            }
        )
    )
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
