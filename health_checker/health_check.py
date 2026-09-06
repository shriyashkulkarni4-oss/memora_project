#!/usr/bin/env python3
"""Check Memoryhive service health in local, Docker, or Kubernetes mode."""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Service:
    name: str
    port: int
    path: str | None = None
    container: str | None = None
    deployment: str | None = None


SERVICES = {
    "backend": Service(
        "backend", 8000, "/health/ready", "memoryhive-backend-1", "backend"
    ),
    "frontend": Service("frontend", 3000, "/", "memoryhive-frontend-1", "frontend"),
    "worker": Service("worker", 0, None, "memoryhive-worker-1", "worker"),
    "db": Service("db", 5432, None, "memoryhive-db-1", None),
    "redis": Service("redis", 6379, None, "memoryhive-redis-1", None),
    "minio": Service("minio", 9000, "/minio/health/ready", "memoryhive-minio-1", None),
}


def check_tcp(host: str, port: int, timeout: float) -> tuple[bool, str]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = (time.perf_counter() - started) * 1000
            return True, f"tcp ok {elapsed:.0f}ms"
    except OSError as exc:
        return False, str(exc)


def check_http(host: str, service: Service, timeout: float) -> tuple[bool, str]:
    started = time.perf_counter()
    url = f"http://{host}:{service.port}{service.path or '/'}"
    try:
        request = Request(url, headers={"Host": host})
        with urlopen(request, timeout=timeout) as response:
            elapsed = (time.perf_counter() - started) * 1000
            return (
                200 <= response.status < 500,
                f"http {response.status} {elapsed:.0f}ms",
            )
    except URLError as exc:
        return False, str(exc.reason)


def docker_health(service: Service) -> tuple[bool, str] | None:
    if not service.container or not shutil.which("docker"):
        return None
    try:
        output = subprocess.check_output(
            [
                "docker",
                "inspect",
                "--format",
                "{{json .State.Health}} {{.State.Status}}",
                service.container,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return False, "container not found"
    health_raw, _, status = output.partition(" ")
    if health_raw and health_raw != "null":
        health = json.loads(health_raw)
        return health.get("Status") == "healthy", health.get("Status", "unknown")
    return status == "running", status


def k8s_health(namespace: str, service: Service) -> tuple[bool, str]:
    if not service.deployment or not shutil.which("kubectl"):
        return False, "no kubectl deployment probe"
    try:
        output = subprocess.check_output(
            [
                "kubectl",
                "-n",
                namespace,
                "get",
                "deployment",
                service.deployment,
                "-o",
                "json",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return False, "deployment not found"
    payload = json.loads(output)
    desired = payload.get("spec", {}).get("replicas", 1)
    ready = payload.get("status", {}).get("readyReplicas", 0)
    available = payload.get("status", {}).get("availableReplicas", 0)
    ok = ready >= desired and available >= desired
    return ok, f"ready {ready}/{desired}, available {available}/{desired}"


def selected_services(names: Iterable[str]) -> list[Service]:
    if not names:
        return list(SERVICES.values())
    unknown = sorted(set(names) - set(SERVICES))
    if unknown:
        raise SystemExit(f"Unknown service(s): {', '.join(unknown)}")
    return [SERVICES[name] for name in names]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["local", "docker", "k8s"], default="local")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--namespace", default="memoryhive-local")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("services", nargs="*")
    args = parser.parse_args()

    failed = False
    for service in selected_services(args.services):
        if args.mode == "k8s":
            ok, message = k8s_health(args.namespace, service)
        elif args.mode == "docker":
            checked = docker_health(service)
            ok, message = checked if checked else (False, "docker unavailable")
        elif service.path:
            ok, message = check_http(args.host, service, args.timeout)
        elif service.port:
            ok, message = check_tcp(args.host, service.port, args.timeout)
        else:
            ok, message = False, "no local probe"
        status = "ok" if ok else "fail"
        print(f"{status:4} {service.name:8} {message}")
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
