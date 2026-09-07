#!/usr/bin/env python3
"""Fail clearly when a selected runtime profile's host ports are occupied."""

from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "service-registry.json"


def available(port: int) -> bool:
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", choices=("infra", "app-only", "full", "temporal"))
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    by_key = {item["key"]: item for item in registry["services"]}
    conflicts = []
    for key in registry["profiles"][args.profile]:
        service = by_key[key]
        default = service.get("host_port")
        if not default:
            continue
        port = int(os.getenv(service.get("host_port_env", ""), str(default)))
        if not available(port):
            conflicts.append((key, port))
    if conflicts:
        for key, port in conflicts:
            print(f"port conflict: {key} requires localhost:{port}")
        print("Stop the owning process/container or choose another port in .env.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
