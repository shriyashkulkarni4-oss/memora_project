#!/usr/bin/env python3
"""Run Memoryhive infrastructure in Docker and application services locally."""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

RUNTIME_ROOT = Path(__file__).resolve().parent
BUILD_ROOT = RUNTIME_ROOT.parent
REPO_ROOT = BUILD_ROOT.parent
REGISTRY = BUILD_ROOT / "service-registry.json"
PIDS = RUNTIME_ROOT / ".pids"
LOGS = RUNTIME_ROOT / ".logs"


def registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def load_env() -> dict[str, str]:
    values = dict(os.environ)
    path = Path(values.get("ENV_FILE", REPO_ROOT / ".env"))
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values.setdefault(key, value)
    values.update(
        {
            "DATABASE_URL": f"postgresql+asyncpg://{values.get('POSTGRES_USER', 'memoryhive')}:{values.get('POSTGRES_PASSWORD', 'memoryhive123')}@127.0.0.1:{values.get('POSTGRES_PORT', '5432')}/{values.get('POSTGRES_DB', 'memoryhive')}",
            "REDIS_URL": f"redis://127.0.0.1:{values.get('REDIS_PORT', '6379')}/0",
            "MINIO_ENDPOINT": f"127.0.0.1:{values.get('MINIO_API_PORT', '9000')}",
        }
    )
    return values


def app_services(profile: str) -> list[dict[str, Any]]:
    data = registry()
    active = set(data["profiles"][profile])
    by_key = {item["key"]: item for item in data["services"]}
    selected = [by_key[key] for key in data["profiles"][profile] if by_key[key]["kind"] in {"service", "process", "frontend"}]
    ordered: list[dict[str, Any]] = []
    pending = list(selected)
    while pending:
        ready = [item for item in pending if all(dep not in active or dep not in {candidate["key"] for candidate in pending} for dep in item["depends_on"])]
        if not ready:
            raise SystemExit("Cycle detected in local service dependency graph")
        for item in ready:
            ordered.append(item)
            pending.remove(item)
    return ordered


def ensure_port(service: dict[str, Any], env: dict[str, str]) -> None:
    port = service.get("host_port")
    if not port:
        return
    port = int(env.get(service.get("host_port_env", ""), str(port)))
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise SystemExit(f"Port {port} for {service['key']} is occupied: {exc}") from exc


def command_for(service: dict[str, Any]) -> tuple[list[str], Path]:
    cwd = REPO_ROOT / service["source"]
    command = list(service["command"])
    if service["kind"] != "frontend":
        venv_bin = cwd / ".venv" / "bin"
        candidate = venv_bin / command[0]
        if candidate.exists():
            command[0] = str(candidate)
        elif command[0] == "python" and (venv_bin / "python").exists():
            command[0] = str(venv_bin / "python")
    return command, cwd


def compose(profile: str, *args: str, dry_run: bool) -> None:
    command = ["docker", "compose", "--env-file", str(REPO_ROOT / ".env"), "-f", str(RUNTIME_ROOT / f"docker-compose.{profile}.yml"), *args]
    print("+", " ".join(command))
    if not dry_run:
        subprocess.run(command, cwd=REPO_ROOT, check=True)


def start(profile: str, dry_run: bool) -> None:
    subprocess.run([sys.executable, str(BUILD_ROOT / "scripts" / "generate_runtime.py")], check=True)
    docker_services = ["db", "redis", "minio"]
    if profile == "temporal":
        docker_services.extend(["temporal-db", "temporal", "temporal-ui"])
    if profile != "app-only":
        compose(profile, "up", "--detach", *docker_services, dry_run=dry_run)
    PIDS.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    env = load_env()
    if profile == "temporal":
        env["TEMPORAL_ENABLED"] = "true"
        env["TEMPORAL_ADDRESS"] = "127.0.0.1:7233"
    backend = REPO_ROOT / "cml-memoryhive-backend"
    migrate = [str(backend / ".venv" / "bin" / "alembic") if (backend / ".venv" / "bin" / "alembic").exists() else "alembic", "upgrade", "head"]
    if any(item["key"] == "cml-memoryhive-backend" for item in app_services(profile)):
        print("+", " ".join(migrate))
        if not dry_run:
            subprocess.run(migrate, cwd=backend, env=env, check=True)
    for service in app_services(profile):
        ensure_port(service, env)
        command, cwd = command_for(service)
        print("+", " ".join(command))
        if dry_run:
            continue
        log = (LOGS / f"{service['key']}.log").open("a", encoding="utf-8")
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        (PIDS / f"{service['key']}.pid").write_text(f"{process.pid}\n", encoding="utf-8")


def stop(profile: str, dry_run: bool) -> None:
    for service in reversed(app_services(profile)):
        path = PIDS / f"{service['key']}.pid"
        if not path.exists():
            continue
        pid = int(path.read_text(encoding="utf-8"))
        print(f"stop {service['key']} pid {pid}")
        if not dry_run:
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            path.unlink(missing_ok=True)
    if profile != "app-only":
        compose(profile, "down", dry_run=dry_run)


def status(profile: str) -> int:
    failed = False
    for service in app_services(profile):
        path = PIDS / f"{service['key']}.pid"
        running = False
        if path.exists():
            try:
                os.kill(int(path.read_text(encoding="utf-8")), 0)
                running = True
            except (ProcessLookupError, ValueError):
                pass
        print(f"{'running' if running else 'stopped':7} {service['key']}")
        failed |= not running
    return int(failed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "stop", "restart", "status", "logs", "clean"))
    parser.add_argument("--profile", choices=("infra", "app-only", "full", "temporal"), default="full")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command == "start":
        start(args.profile, args.dry_run)
    elif args.command == "stop":
        stop(args.profile, args.dry_run)
    elif args.command == "restart":
        stop(args.profile, args.dry_run)
        start(args.profile, args.dry_run)
    elif args.command == "status":
        return status(args.profile)
    elif args.command == "logs":
        print(LOGS)
        for path in sorted(LOGS.glob("*.log")):
            print(path)
    else:
        if PIDS.exists() and any(PIDS.iterdir()):
            raise SystemExit("Stop local services before cleaning runtime state")
        for path in (*LOGS.glob("*.log"), *PIDS.glob("*.pid")):
            if not args.dry_run:
                path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
