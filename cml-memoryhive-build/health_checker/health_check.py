#!/usr/bin/env -S uv run
"""Check registry-defined Memoryhive services in local, Docker, or Kubernetes mode."""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

BUILD_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = BUILD_ROOT / "service-registry.json"
PIDS = BUILD_ROOT / "runtime" / ".pids"


def load_services(profile: str) -> dict[str, dict[str, Any]]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if profile not in registry["profiles"]:
        raise SystemExit(f"Unknown profile: {profile}")
    by_key = {service["key"]: service for service in registry["services"]}
    return {key: by_key[key] for key in registry["profiles"][profile]}


def elapsed(started: float) -> str:
    return f"{(time.perf_counter() - started) * 1000:.0f}ms"


def http_check(host: str, port: int, path: str, timeout: float) -> tuple[bool, str]:
    started = time.perf_counter()
    try:
        with urlopen(Request(f"http://{host}:{port}{path}", headers={"Host": host}), timeout=timeout) as response:
            return 200 <= response.status < 500, f"http {response.status} {elapsed(started)}"
    except URLError as exc:
        return False, str(exc.reason)


def tcp_check(host: str, port: int, timeout: float) -> tuple[bool, str]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"tcp ok {elapsed(started)}"
    except OSError as exc:
        return False, str(exc)


def local_check(service: dict[str, Any], host: str, timeout: float) -> tuple[bool, str]:
    probe = service["health"]
    port = int(service.get("host_port", 0))
    if probe["type"] == "http":
        return http_check(host, port, probe.get("path", "/"), timeout)
    if probe["type"] == "tcp":
        return tcp_check(host, port, timeout)
    pid_file = PIDS / f"{service['key']}.pid"
    if not pid_file.exists():
        return False, "pid file not found"
    pid = pid_file.read_text(encoding="utf-8").strip()
    result = subprocess.run(["kill", "-0", pid], check=False, capture_output=True)
    return result.returncode == 0, f"pid {pid} {'running' if result.returncode == 0 else 'stopped'}"


def docker_check(service: dict[str, Any]) -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "docker unavailable"
    key = service["key"]
    container = key if key.startswith("cml-memoryhive-") else f"cml-memoryhive-{key}"
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{json .State.Health}} {{.State.Status}}", container],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return False, "container not found"
    health_raw, _, status = result.stdout.strip().partition(" ")
    if health_raw and health_raw != "null":
        state = json.loads(health_raw).get("Status", "unknown")
        return state == "healthy", state
    return status == "running", status


def kubernetes_check(namespace: str, service: dict[str, Any]) -> tuple[bool, str]:
    key = service["key"]
    workload = {
        "db": ("statefulset", "db"),
        "minio": ("statefulset", "minio"),
        "redis": ("deployment", "redis"),
    }.get(key)
    if key.startswith("cml-memoryhive-"):
        workload = ("deployment", key)
    if workload is None:
        return True, "external to Kubernetes profile"
    if not shutil.which("kubectl"):
        return False, "kubectl unavailable"
    kind, name = workload
    result = subprocess.run(
        ["kubectl", "-n", namespace, "get", kind, name, "-o", "json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return False, f"{kind} not found"
    payload = json.loads(result.stdout)
    desired = payload.get("spec", {}).get("replicas", 1)
    ready = payload.get("status", {}).get("readyReplicas", 0)
    available = payload.get("status", {}).get("availableReplicas", ready)
    return ready >= desired and available >= desired, f"ready {ready}/{desired}, available {available}/{desired}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("local", "docker", "k8s"), default="local")
    parser.add_argument("--profile", choices=("infra", "app-only", "full", "temporal"), default="full")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--namespace", default="cml-memoryhive-local")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("services", nargs="*")
    args = parser.parse_args()
    available = load_services(args.profile)
    requested = args.services or list(available)
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise SystemExit(f"Services not in {args.profile} profile: {', '.join(unknown)}")
    failed = False
    for key in requested:
        service = available[key]
        if args.mode == "docker":
            ok, message = docker_check(service)
        elif args.mode == "k8s":
            ok, message = kubernetes_check(args.namespace, service)
        else:
            ok, message = local_check(service, args.host, args.timeout)
        print(f"{'ok' if ok else 'fail':4} {key:36} {message}")
        failed |= not ok
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
