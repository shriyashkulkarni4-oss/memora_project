#!/usr/bin/env -S uv run
"""Fail clearly when a selected runtime profile's host ports are occupied."""

from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "service-registry.json"
REPO_ROOT = REGISTRY.parent.parent


def load_environment(path: Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if path and path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
    values.update(os.environ)
    return values


def available(port: int) -> bool:
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def profile_conflicts(
    profile: str, environment: dict[str, str] | None = None
) -> list[tuple[str, int]]:
    environment = environment or dict(os.environ)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    by_key = {item["key"]: item for item in registry["services"]}
    conflicts = []
    for key in registry["profiles"][profile]:
        service = by_key[key]
        declared = [service, *service.get("additional_ports", [])]
        for item in declared:
            default = item.get("host_port")
            if not default:
                continue
            port = int(environment.get(item.get("host_port_env", ""), str(default)))
            if not available(port):
                label = key if item is service else f"{key}:{item['name']}"
                conflicts.append((label, port))
    return conflicts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", choices=("infra", "app-only", "full", "temporal"))
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(os.environ.get("ENV_FILE", REPO_ROOT / ".env")),
    )
    args = parser.parse_args()
    conflicts = profile_conflicts(args.profile, load_environment(args.env_file))
    if conflicts:
        for key, port in conflicts:
            print(f"port conflict: {key} requires localhost:{port}")
        print("Stop the owning process/container or choose another port in .env.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
