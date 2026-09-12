#!/usr/bin/env python3
"""Exercise the running API and Temporal service with all capture variants."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from temporalio.client import Client

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
TERMINAL = {"analyzed", "degraded", "failed"}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument(
        "--temporal-address", default=os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    )
    parser.add_argument(
        "--namespace", default=os.getenv("TEMPORAL_NAMESPACE", "default")
    )
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation-results/temporal-acceptance.json"),
    )
    return parser.parse_args()


async def wait_for_item(
    client: httpx.AsyncClient, item_id: str, timeout: int
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = await client.get(f"/api/v1/items/{item_id}")
        response.raise_for_status()
        item = response.json()
        if item["analysis_status"] in TERMINAL:
            return item
        await asyncio.sleep(1)
    raise TimeoutError(f"item {item_id} did not reach a terminal analysis state")


async def main() -> int:
    args = arguments()
    report: dict[str, object] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "namespace": args.namespace,
        "captures": [],
        "passed": False,
        "sanitized": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with httpx.AsyncClient(
            base_url=f"{args.base_url.rstrip('/')}/api/v1", timeout=20
        ) as api:
            email = f"temporal-acceptance-{uuid.uuid4()}@example.invalid"
            password = f"Acceptance-{uuid.uuid4()}"
            register = await api.post(
                "/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "name": "Temporal Acceptance",
                },
            )
            register.raise_for_status()
            login = await api.post(
                "/auth/login", json={"email": email, "password": password}
            )
            login.raise_for_status()
            api.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
            requests = [
                (
                    "text",
                    await api.post(
                        "/items",
                        json={
                            "type": "text",
                            "title": "Synthetic Temporal text",
                            "raw_text": "A synthetic acceptance item verifies durable workflow execution.",
                        },
                    ),
                ),
                (
                    "link",
                    await api.post(
                        "/items",
                        json={
                            "type": "link",
                            "title": "Synthetic Temporal link",
                            "url": "https://example.com/",
                        },
                    ),
                ),
                (
                    "screenshot",
                    await api.post(
                        "/items/screenshot",
                        data={"title": "Synthetic Temporal screenshot"},
                        files={"file": ("synthetic.png", PNG_1X1, "image/png")},
                    ),
                ),
            ]
            temporal = await Client.connect(
                args.temporal_address, namespace=args.namespace
            )
            for item_type, response in requests:
                response.raise_for_status()
                created = response.json()
                item = await wait_for_item(api, created["id"], args.timeout_seconds)
                workflow_id = f"memoryhive-analysis-{created['id']}-v{created['analysis_version']}"
                handle = temporal.get_workflow_handle(workflow_id)
                history = await handle.fetch_history()
                if not history.events:
                    raise AssertionError(f"workflow {workflow_id} has no event history")
                report["captures"].append(
                    {
                        "item_type": item_type,
                        "item_id": created["id"],
                        "workflow_id": workflow_id,
                        "analysis_status": item["analysis_status"],
                        "processing_status": item["processing_status"],
                        "history_event_count": len(history.events),
                    }
                )
            metrics = await api.get(f"{args.base_url.rstrip('/')}/metrics")
            report["metrics_snapshot"] = (
                [
                    line
                    for line in metrics.text.splitlines()
                    if line.startswith("memoryhive_")
                    and not line.startswith("memoryhive_http_request")
                ][:200]
                if metrics.is_success
                else []
            )
            report["passed"] = True
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
