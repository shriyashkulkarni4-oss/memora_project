#!/usr/bin/env -S uv run
"""Check registry-defined Memoryhive services in local, Docker, or Kubernetes mode."""

from __future__ import annotations

import argparse
import json
import os
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
HEALTH_ROOT = BUILD_ROOT / "health_checker"
PIDS = BUILD_ROOT / "runtime" / ".pids"


def load_services(profile: str) -> dict[str, dict[str, Any]]:
    path = HEALTH_ROOT / f"health-registry.{profile}.json"
    if not path.is_file():
        raise SystemExit(f"Missing generated health registry: {path}")
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("profile") != profile or not isinstance(
        registry.get("services"), dict
    ):
        raise SystemExit(f"Invalid generated health registry: {path}")
    return registry["services"]


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


def elapsed(started: float) -> str:
    return f"{(time.perf_counter() - started) * 1000:.0f}ms"


def http_check(host: str, port: int, path: str, timeout: float) -> tuple[bool, str]:
    started = time.perf_counter()
    try:
        with urlopen(
            Request(f"http://{host}:{port}{path}", headers={"Host": host}),
            timeout=timeout,
        ) as response:
            return (
                200 <= response.status < 500,
                f"http {response.status} {elapsed(started)}",
            )
    except URLError as exc:
        return False, str(exc.reason)


def tcp_check(host: str, port: int, timeout: float) -> tuple[bool, str]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"tcp ok {elapsed(started)}"
    except OSError as exc:
        return False, str(exc)


def local_check(
    service: dict[str, Any],
    host: str,
    timeout: float,
    environment: dict[str, str],
) -> tuple[bool, str]:
    probe = service["health"]
    port = int(
        environment.get(service.get("host_port_env") or "", service.get("port", 0))
    )
    if probe["type"] == "http":
        return http_check(host, port, probe.get("path", "/"), timeout)
    if probe["type"] == "tcp":
        return tcp_check(host, port, timeout)
    if service["kind"] == "infra":
        return docker_check(service, host, timeout, environment)
    pid_file = PIDS / f"{service['key']}.pid"
    if not pid_file.exists():
        return False, "pid file not found"
    pid = pid_file.read_text(encoding="utf-8").strip()
    result = subprocess.run(["kill", "-0", pid], check=False, capture_output=True)
    return (
        result.returncode == 0,
        f"pid {pid} {'running' if result.returncode == 0 else 'stopped'}",
    )


def docker_check(
    service: dict[str, Any],
    host: str = "127.0.0.1",
    timeout: float = 3.0,
    environment: dict[str, str] | None = None,
) -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "docker unavailable"
    container = service["container"]
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{json .State}}", container],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return False, "container not found"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, "invalid docker inspect response"
    health = payload.get("Health")
    if health:
        state = health.get("Status", "unknown")
        return state == "healthy", state
    status = payload.get("Status", "unknown")
    if status != "running":
        return False, status
    probe = service.get("health", {})
    port = int(
        (environment or {}).get(
            service.get("host_port_env") or "", service.get("port", 0)
        )
    )
    if probe.get("type") == "http" and port:
        return http_check(host, port, probe.get("path", "/"), timeout)
    if probe.get("type") == "tcp" and port:
        return tcp_check(host, port, timeout)
    return True, status


def kubernetes_check(namespace: str, service: dict[str, Any]) -> tuple[bool, str]:
    workload = service.get("kubernetes")
    if not workload:
        return True, "external to Kubernetes profile"
    if not shutil.which("kubectl"):
        return False, "kubectl unavailable"
    kind, name = workload["kind"], workload["name"]
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
    return (
        ready >= desired and available >= desired,
        f"ready {ready}/{desired}, available {available}/{desired}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("local", "docker", "k8s"), default="local")
    parser.add_argument(
        "--profile", choices=("infra", "app-only", "full", "temporal"), default="full"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--namespace", default="cml-memoryhive-local")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(os.environ.get("ENV_FILE", BUILD_ROOT.parent / ".env")),
    )
    parser.add_argument("services", nargs="*")
    args = parser.parse_args()
    available = load_services(args.profile)
    requested = args.services or list(available)
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise SystemExit(
            f"Services not in {args.profile} profile: {', '.join(unknown)}"
        )
    failed = False
    environment = load_environment(args.env_file)
    for key in requested:
        service = available[key]
        if args.mode == "docker":
            ok, message = docker_check(service, args.host, args.timeout, environment)
        elif args.mode == "k8s":
            ok, message = kubernetes_check(args.namespace, service)
        else:
            ok, message = local_check(service, args.host, args.timeout, environment)
        print(f"{'ok' if ok else 'fail':4} {key:36} {message}")
        failed |= not ok
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
