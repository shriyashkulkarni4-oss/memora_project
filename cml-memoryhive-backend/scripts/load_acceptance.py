#!/usr/bin/env python3
"""Bounded local capture-burst, backlog-drain, and search-latency acceptance test."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--captures", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--search-p95-limit-ms", type=float, default=2000)
    parser.add_argument(
        "--output", type=Path, default=Path("evaluation-results/load-acceptance.json")
    )
    return parser.parse_args()


async def main() -> int:
    args = arguments()
    if not 1 <= args.captures <= 100:
        raise ValueError("captures must be between 1 and 100")
    report: dict[str, object] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "captures": args.captures,
        "sanitized": True,
        "passed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with httpx.AsyncClient(
            base_url=f"{args.base_url.rstrip('/')}/api/v1", timeout=20
        ) as api:
            email = f"load-acceptance-{uuid.uuid4()}@example.invalid"
            password = f"Acceptance-{uuid.uuid4()}"
            register = await api.post(
                "/auth/register", json={"email": email, "password": password}
            )
            register.raise_for_status()
            login = await api.post(
                "/auth/login", json={"email": email, "password": password}
            )
            login.raise_for_status()
            api.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

            started = time.perf_counter()
            responses = await asyncio.gather(
                *[
                    api.post(
                        "/items",
                        json={
                            "type": "text",
                            "title": f"Synthetic burst {index}",
                            "raw_text": f"Synthetic burst content {index} about durable retrieval.",
                        },
                    )
                    for index in range(args.captures)
                ]
            )
            if any(response.status_code != 201 for response in responses):
                raise AssertionError("capture burst returned a non-201 response")
            pending = [response.json()["id"] for response in responses]
            report["capture_burst_ms"] = round(
                (time.perf_counter() - started) * 1000, 2
            )

            deadline = time.monotonic() + args.timeout_seconds
            maximum_backlog = len(pending)
            while pending and time.monotonic() < deadline:
                states = await asyncio.gather(
                    *[api.get(f"/items/{item_id}") for item_id in pending]
                )
                pending = [
                    item_id
                    for item_id, response in zip(pending, states, strict=True)
                    if response.json()["analysis_status"]
                    not in {"analyzed", "degraded", "failed"}
                ]
                maximum_backlog = max(maximum_backlog, len(pending))
                if pending:
                    await asyncio.sleep(1)
            if pending:
                raise TimeoutError(
                    "analysis backlog did not drain within the acceptance window"
                )

            latencies = []
            for _ in range(10):
                before = time.perf_counter()
                response = await api.get(
                    "/items", params={"q": "durable retrieval", "limit": 30}
                )
                response.raise_for_status()
                latencies.append((time.perf_counter() - before) * 1000)
            latencies.sort()
            p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]
            if p95 > args.search_p95_limit_ms:
                raise AssertionError(f"search p95 {p95:.2f} ms exceeds limit")
            report.update(
                {
                    "maximum_analysis_backlog": maximum_backlog,
                    "remaining_backlog": 0,
                    "search_p95_ms": round(p95, 2),
                    "passed": True,
                }
            )
            return 0
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
        return 1
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
