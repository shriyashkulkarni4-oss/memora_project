#!/usr/bin/env python3
"""Generate Compose profiles and health registries from service-registry.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BUILD_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILD_ROOT.parent
REGISTRY_PATH = BUILD_ROOT / "service-registry.json"
RUNTIME_ROOT = BUILD_ROOT / "runtime"
HEALTH_ROOT = BUILD_ROOT / "health_checker"


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def container_name(key: str) -> str:
    return key if key.startswith("cml-memoryhive-") else f"cml-memoryhive-{key}"


def backend_environment(*, temporal: bool) -> dict[str, str]:
    return {
        "ENVIRONMENT": "development",
        "APP_DEBUG": "true",
        "DATABASE_URL": "${DATABASE_URL:-postgresql+asyncpg://memoryhive:memoryhive123@db:5432/memoryhive}",
        "REDIS_URL": "${REDIS_URL:-redis://redis:6379/0}",
        "MINIO_ENDPOINT": "${MINIO_ENDPOINT:-minio:9000}",
        "MINIO_ACCESS_KEY": "${MINIO_ROOT_USER:-minioadmin}",
        "MINIO_SECRET_KEY": "${MINIO_ROOT_PASSWORD:-minioadmin123}",
        "MINIO_BUCKET": "${MINIO_BUCKET:-memoryhive-uploads}",
        "MINIO_SECURE": "false",
        "JWT_SECRET_KEY": "${JWT_SECRET_KEY:-dev-secret-key-change-before-production}",
        "JWT_ALGORITHM": "${JWT_ALGORITHM:-HS256}",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "${ACCESS_TOKEN_EXPIRE_MINUTES:-1440}",
        "REFRESH_TOKEN_EXPIRE_DAYS": "${REFRESH_TOKEN_EXPIRE_DAYS:-30}",
        "ENCRYPTION_KEY": "${ENCRYPTION_KEY:-dev-encryption-key-32-bytes-long!}",
        "CORS_ORIGINS": "${CORS_ORIGINS:-[\"http://localhost:3000\"]}",
        "TEMPORAL_ENABLED": "true" if temporal else "false",
        "TEMPORAL_ADDRESS": "${TEMPORAL_ADDRESS:-temporal:7233}",
        "TEMPORAL_NAMESPACE": "${TEMPORAL_NAMESPACE:-default}",
        "TEMPORAL_TASK_QUEUE": "${TEMPORAL_TASK_QUEUE:-memoryhive-analysis}",
        "TEMPORAL_SCHEDULER_POLL_SECONDS": "${TEMPORAL_SCHEDULER_POLL_SECONDS:-10}",
        "TEMPORAL_SCHEDULER_BATCH_SIZE": "${TEMPORAL_SCHEDULER_BATCH_SIZE:-25}",
        "N8N_WEBHOOK_URL": "${N8N_WEBHOOK_URL:-}",
        "N8N_API_KEY": "${N8N_API_KEY:-}",
        "OLLAMA_BASE_URL": "${OLLAMA_BASE_URL:-}",
        "OLLAMA_MODEL": "${OLLAMA_MODEL:-qwen2.5:3b}",
    }


def depends_on(active: set[str], dependencies: list[str]) -> dict[str, Any]:
    return {
        dependency: {
            "condition": "service_healthy"
            if dependency in {"db", "redis", "minio", "temporal-db"}
            else "service_started"
        }
        for dependency in dependencies
        if dependency in active
    }


def build_service(key: str, active: set[str]) -> dict[str, Any]:
    temporal_enabled = key.startswith("cml-memoryhive-temporal-")
    backend_env = backend_environment(temporal=temporal_enabled)
    source = "../../cml-memoryhive-backend"
    if key == "db":
        return {
            "container_name": container_name(key),
            "image": "postgres:15-alpine",
            "environment": {
                "POSTGRES_USER": "${POSTGRES_USER:-memoryhive}",
                "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD:-memoryhive123}",
                "POSTGRES_DB": "${POSTGRES_DB:-memoryhive}",
            },
            "ports": ["${POSTGRES_PORT:-5432}:5432"],
            "volumes": ["pgdata:/var/lib/postgresql/data"],
            "healthcheck": {
                "test": ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"],
                "interval": "5s",
                "timeout": "5s",
                "retries": 10,
            },
            "restart": "unless-stopped",
        }
    if key == "redis":
        return {
            "container_name": container_name(key),
            "image": "redis:7-alpine",
            "command": ["redis-server", "--save", "60", "1", "--loglevel", "warning"],
            "ports": ["${REDIS_PORT:-6379}:6379"],
            "volumes": ["redisdata:/data"],
            "healthcheck": {"test": ["CMD", "redis-cli", "ping"], "interval": "5s", "timeout": "3s", "retries": 10},
            "restart": "unless-stopped",
        }
    if key == "minio":
        return {
            "container_name": container_name(key),
            "image": "minio/minio:latest",
            "command": ["server", "/data", "--console-address", ":9001"],
            "environment": {"MINIO_ROOT_USER": "${MINIO_ROOT_USER:-minioadmin}", "MINIO_ROOT_PASSWORD": "${MINIO_ROOT_PASSWORD:-minioadmin123}"},
            "ports": ["${MINIO_API_PORT:-9000}:9000", "${MINIO_CONSOLE_PORT:-9001}:9001"],
            "volumes": ["miniodata:/data"],
            "healthcheck": {"test": ["CMD", "curl", "--fail", "--silent", "http://localhost:9000/minio/health/ready"], "interval": "10s", "timeout": "5s", "retries": 10},
            "restart": "unless-stopped",
        }
    if key == "temporal-db":
        return {
            "container_name": container_name(key),
            "image": "postgres:15-alpine",
            "environment": {"POSTGRES_USER": "temporal", "POSTGRES_PASSWORD": "temporal"},
            "volumes": ["temporal_pgdata:/var/lib/postgresql/data"],
            "healthcheck": {"test": ["CMD-SHELL", "pg_isready -U temporal"], "interval": "5s", "timeout": "5s", "retries": 20},
            "restart": "unless-stopped",
        }
    if key == "temporal":
        return {
            "container_name": container_name(key),
            "image": "temporalio/auto-setup:${TEMPORAL_VERSION:-latest}",
            "environment": {"DB": "postgres12", "DB_PORT": "5432", "POSTGRES_USER": "temporal", "POSTGRES_PWD": "temporal", "POSTGRES_SEEDS": "temporal-db", "DYNAMIC_CONFIG_FILE_PATH": "config/dynamicconfig/development-sql.yaml"},
            "ports": ["${TEMPORAL_PORT:-7233}:7233"],
            "volumes": ["../../ops/temporal/dynamicconfig:/etc/temporal/config/dynamicconfig:ro"],
            "depends_on": depends_on(active, ["temporal-db"]),
            "restart": "unless-stopped",
        }
    if key == "temporal-ui":
        return {
            "container_name": container_name(key),
            "image": "temporalio/ui:${TEMPORAL_UI_VERSION:-latest}",
            "environment": {"TEMPORAL_ADDRESS": "temporal:7233", "TEMPORAL_CORS_ORIGINS": "http://localhost:${FRONTEND_PORT:-3000}"},
            "ports": ["${TEMPORAL_UI_PORT:-8088}:8080"],
            "depends_on": depends_on(active, ["temporal"]),
            "restart": "unless-stopped",
        }
    if key == "cml-memoryhive-frontend":
        return {
            "container_name": container_name(key),
            "build": {"context": "../../cml-memoryhive-frontend", "dockerfile": "Dockerfile", "target": "development"},
            "environment": {"VITE_API_URL": "${VITE_API_URL:-/api/v1}", "VITE_SUPPORT_EMAIL": "${VITE_SUPPORT_EMAIL:-support@memoryhive.example.com}", "VITE_PROXY_TARGET": "http://cml-memoryhive-backend:8000"},
            "ports": ["${FRONTEND_PORT:-3000}:3000"],
            "depends_on": depends_on(active, ["cml-memoryhive-backend"]),
            "volumes": ["../../cml-memoryhive-frontend:/app", "frontend_node_modules:/app/node_modules"],
            "healthcheck": {"test": ["CMD", "wget", "--quiet", "--output-document=/dev/null", "http://127.0.0.1:3000/"], "interval": "10s", "timeout": "5s", "retries": 10},
            "restart": "unless-stopped",
        }
    commands = {
        "cml-memoryhive-backend": ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        "cml-memoryhive-worker": ["python", "-m", "app.worker"],
        "cml-memoryhive-temporal-worker": ["python", "-m", "app.temporal_pipeline.worker"],
        "cml-memoryhive-temporal-scheduler": ["python", "-m", "app.temporal_pipeline.scheduler"],
    }
    service = {
        "container_name": container_name(key),
        "build": {"context": source, "dockerfile": "Dockerfile", "target": "development"},
        "command": commands[key],
        "environment": backend_env,
        "depends_on": depends_on(active, next(item["depends_on"] for item in load_registry()["services"] if item["key"] == key)),
        "volumes": [f"{source}:/app"],
        "restart": "unless-stopped",
    }
    if key == "cml-memoryhive-backend":
        service["ports"] = ["${BACKEND_PORT:-8000}:8000"]
        service["healthcheck"] = {"test": ["CMD", "curl", "--fail", "--silent", "http://localhost:8000/health/ready"], "interval": "10s", "timeout": "5s", "retries": 10}
    else:
        marker = commands[key][-1]
        service["healthcheck"] = {"test": ["CMD", "python", "-c", f"import pathlib,sys; sys.exit(0 if b'{marker}' in pathlib.Path('/proc/1/cmdline').read_bytes() else 1)"], "interval": "15s", "timeout": "5s", "retries": 3}
    return service


def render_profile(registry: dict[str, Any], profile: str) -> dict[str, Any]:
    active = set(registry["profiles"][profile])
    services = {key: build_service(key, active) for key in registry["profiles"][profile]}
    if "cml-memoryhive-backend" in active:
        services["migrate"] = {
            "container_name": "cml-memoryhive-migrate",
            "build": {"context": "../../cml-memoryhive-backend", "dockerfile": "Dockerfile", "target": "development"},
            "command": ["alembic", "upgrade", "head"],
            "environment": backend_environment(temporal=False),
            "depends_on": depends_on(active, ["db"]),
            "volumes": ["../../cml-memoryhive-backend:/app"],
            "restart": "no",
        }
        for key in active:
            if key.startswith("cml-memoryhive-") and key != "cml-memoryhive-frontend":
                services[key].setdefault("depends_on", {})["migrate"] = {"condition": "service_completed_successfully"}
    return {
        "name": "cml-memoryhive",
        "services": services,
        "volumes": {name: {} for name in ("pgdata", "redisdata", "miniodata", "temporal_pgdata", "frontend_node_modules")},
        "networks": {"default": {"name": "cml-memoryhive-network"}},
    }


def main() -> int:
    registry = load_registry()
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    HEALTH_ROOT.mkdir(parents=True, exist_ok=True)
    services_by_key = {service["key"]: service for service in registry["services"]}
    for profile in registry["profiles"]:
        compose_path = RUNTIME_ROOT / f"docker-compose.{profile}.yml"
        compose_path.write_text(json.dumps(render_profile(registry, profile), indent=2) + "\n", encoding="utf-8")
        health = {
            "profile": profile,
            "services": {
                key: {
                    "kind": services_by_key[key]["kind"],
                    "host": "127.0.0.1",
                    "port": services_by_key[key].get("host_port", 0),
                    "health": services_by_key[key]["health"],
                    "container": container_name(key),
                    "deployment": key if key.startswith("cml-memoryhive-") else None,
                }
                for key in registry["profiles"][profile]
            },
        }
        (HEALTH_ROOT / f"health-registry.{profile}.json").write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")
    (RUNTIME_ROOT / "docker-compose.yml").write_text((RUNTIME_ROOT / "docker-compose.full.yml").read_text(encoding="utf-8"), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
