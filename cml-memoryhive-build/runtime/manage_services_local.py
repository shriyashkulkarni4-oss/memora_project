#!/usr/bin/env -S uv run
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
START_TIMEOUT_SECONDS = os.environ.get("START_TIMEOUT_SECONDS", "180")


def registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def runtime_env_file() -> Path:
    configured = os.environ.get("ENV_FILE")
    if configured:
        return Path(configured)
    local = REPO_ROOT / ".env"
    return local if local.is_file() else REPO_ROOT / ".env.example"


def load_env() -> dict[str, str]:
    values = dict(os.environ)
    path = runtime_env_file()
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
    values.setdefault(
        "VITE_PROXY_TARGET",
        f"http://127.0.0.1:{values.get('BACKEND_PORT', '8000')}",
    )
    return values


def app_services(profile: str) -> list[dict[str, Any]]:
    data = registry()
    active = set(data["profiles"][profile])
    by_key = {item["key"]: item for item in data["services"]}
    selected = [
        by_key[key]
        for key in data["profiles"][profile]
        if by_key[key]["kind"] in {"service", "process", "frontend"}
    ]
    ordered: list[dict[str, Any]] = []
    pending = list(selected)
    while pending:
        ready = [
            item
            for item in pending
            if all(
                dep not in active
                or dep not in {candidate["key"] for candidate in pending}
                for dep in item["depends_on"]
            )
        ]
        if not ready:
            raise SystemExit("Cycle detected in local service dependency graph")
        for item in ready:
            ordered.append(item)
            pending.remove(item)
    return ordered


def ensure_port(service: dict[str, Any], env: dict[str, str]) -> None:
    declared = [service, *service.get("additional_ports", [])]
    for item in declared:
        default = item.get("host_port")
        if not default:
            continue
        port = int(env.get(item.get("host_port_env", ""), str(default)))
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError as exc:
                label = service["key"]
                if item is not service:
                    label = f"{label}:{item['name']}"
                raise SystemExit(f"Port {port} for {label} is occupied: {exc}") from exc


def command_for(
    service: dict[str, Any], environment: dict[str, str]
) -> tuple[list[str], Path]:
    cwd = REPO_ROOT / service["source"]
    command = list(service["command"])
    port_env = service.get("host_port_env")
    if port_env and "--port" in command:
        port_index = command.index("--port") + 1
        command[port_index] = environment.get(
            port_env, str(service.get("host_port", service["port"]))
        )
    return command, cwd


def process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def clean_stale_pid_files() -> None:
    PIDS.mkdir(exist_ok=True)
    for path in PIDS.glob("*.pid"):
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
        except ValueError:
            path.unlink(missing_ok=True)
            continue
        if not process_running(pid):
            path.unlink(missing_ok=True)


def compose(profile: str, *args: str, dry_run: bool) -> None:
    command = [
        "docker",
        "compose",
        "--env-file",
        str(runtime_env_file()),
        "-f",
        str(RUNTIME_ROOT / f"docker-compose.{profile}.yml"),
        *args,
    ]
    print("+", " ".join(command))
    if not dry_run:
        subprocess.run(command, cwd=REPO_ROOT, check=True)


def start(profile: str, dry_run: bool) -> None:
    subprocess.run(
        [sys.executable, str(BUILD_ROOT / "scripts" / "generate_runtime.py")],
        check=True,
    )
    clean_stale_pid_files()
    selected = app_services(profile)
    running = [
        service["key"]
        for service in selected
        if (PIDS / f"{service['key']}.pid").exists()
    ]
    if running:
        raise SystemExit(f"Local services already running: {', '.join(running)}")
    env = load_env()
    data = registry()
    by_key = {item["key"]: item for item in data["services"]}
    for key in data["profiles"][profile]:
        ensure_port(by_key[key], env)
    docker_services = ["db", "redis", "minio"]
    if profile == "temporal":
        docker_services.extend(["temporal-db", "temporal", "temporal-ui"])
    if profile != "app-only":
        compose(
            profile,
            "up",
            "--detach",
            "--wait",
            "--wait-timeout",
            START_TIMEOUT_SECONDS,
            *docker_services,
            dry_run=dry_run,
        )
    LOGS.mkdir(exist_ok=True)
    if profile == "temporal":
        env["TEMPORAL_ENABLED"] = "true"
        env["TEMPORAL_ADDRESS"] = "127.0.0.1:7233"
    backend = REPO_ROOT / "cml-memoryhive-backend"
    migrate = ["uv", "run", "--frozen", "alembic", "upgrade", "head"]
    if any(item["key"] == "cml-memoryhive-backend" for item in selected):
        print("+", " ".join(migrate))
        if not dry_run:
            subprocess.run(migrate, cwd=backend, env=env, check=True)
    for service in selected:
        command, cwd = command_for(service, env)
        print("+", " ".join(command))
        if dry_run:
            continue
        with (LOGS / f"{service['key']}.log").open("a", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        (PIDS / f"{service['key']}.pid").write_text(
            f"{process.pid}\n", encoding="utf-8"
        )


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
    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_ROOT / "health_checker" / "health_check.py"),
            "--mode",
            "local",
            "--profile",
            profile,
        ],
        cwd=REPO_ROOT,
        check=False,
    )
    return result.returncode


def clean(dry_run: bool) -> None:
    active: list[Path] = []
    for path in PIDS.glob("*.pid"):
        try:
            if process_running(int(path.read_text(encoding="utf-8").strip())):
                active.append(path)
        except ValueError:
            continue
    if active:
        names = ", ".join(path.stem for path in active)
        raise SystemExit(f"Stop local services before cleaning runtime state: {names}")
    for path in (*LOGS.glob("*.log"), *PIDS.glob("*.pid")):
        print(f"clean {path}")
        if not dry_run:
            path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("start", "stop", "restart", "status", "logs", "clean")
    )
    parser.add_argument(
        "--profile", choices=("infra", "app-only", "full", "temporal"), default="full"
    )
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
        clean(args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
