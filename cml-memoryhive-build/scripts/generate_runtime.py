#!/usr/bin/env -S uv run
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


def validate_registry(registry: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "app",
        "registry",
        "registry_namespace",
        "platforms",
        "images",
        "profiles",
        "services",
    }
    missing = required - registry.keys()
    if missing:
        raise ValueError(f"Service registry is missing fields: {sorted(missing)}")
    if registry["schema_version"] != 1 or registry["app"] != "cml-memoryhive":
        raise ValueError("Service registry has an unsupported schema or app identity")
    if not isinstance(registry["platforms"], list) or not registry["platforms"]:
        raise ValueError("Service registry platforms must be a non-empty list")
    if not isinstance(registry["images"], list) or not registry["images"]:
        raise ValueError("Service registry images must be a non-empty list")
    image_keys = [image.get("key") for image in registry["images"]]
    if None in image_keys or len(image_keys) != len(set(image_keys)):
        raise ValueError("Service registry image keys must be present and unique")
    for image in registry["images"]:
        missing_image = {
            "key",
            "context",
            "dockerfile",
            "target",
            "runtime_target",
        } - image.keys()
        if missing_image:
            raise ValueError(
                f"Image {image.get('key')!r} is missing fields: {sorted(missing_image)}"
            )

    if not isinstance(registry["services"], list) or not registry["services"]:
        raise ValueError("Service registry services must be a non-empty list")
    service_keys = [service.get("key") for service in registry["services"]]
    if None in service_keys or len(service_keys) != len(set(service_keys)):
        raise ValueError("Service registry service keys must be present and unique")
    known_services = set(service_keys)
    ports: list[int] = []
    graph: dict[str, set[str]] = {}
    for service in registry["services"]:
        key = service["key"]
        missing_service = {"kind", "port", "health", "depends_on"} - service.keys()
        if missing_service:
            raise ValueError(
                f"Service {key!r} is missing fields: {sorted(missing_service)}"
            )
        if service["kind"] not in {"infra", "service", "process", "frontend"}:
            raise ValueError(f"Service {key!r} has an invalid kind")
        health = service["health"]
        if not isinstance(health, dict) or health.get("type") not in {
            "http",
            "tcp",
            "process",
        }:
            raise ValueError(f"Service {key!r} has an invalid health probe")
        dependencies = service["depends_on"]
        if not isinstance(dependencies, list) or set(dependencies) - known_services:
            raise ValueError(f"Service {key!r} has unknown dependencies")
        graph[key] = set(dependencies)
        if service.get("host_port"):
            ports.append(int(service["host_port"]))
        for extra in service.get("additional_ports", []):
            if not {"name", "port", "host_port", "host_port_env"} <= extra.keys():
                raise ValueError(f"Service {key!r} has an invalid additional port")
            ports.append(int(extra["host_port"]))
        if service.get("image_key") not in {None, *image_keys}:
            raise ValueError(f"Service {key!r} has an unknown image mapping")
        if (
            service["kind"] != "infra"
            and not {
                "image_key",
                "source",
                "command",
            }
            <= service.keys()
        ):
            raise ValueError(f"Service {key!r} lacks local runtime/image fields")
        workload = service.get("kubernetes")
        if workload and (
            workload.get("kind") not in {"deployment", "statefulset"}
            or not workload.get("name")
        ):
            raise ValueError(f"Service {key!r} has an invalid Kubernetes workload")
    if len(ports) != len(set(ports)):
        raise ValueError("Service registry host ports must be unique")

    if set(registry["profiles"]) != {
        "infra",
        "app-only",
        "full",
        "temporal",
        "observability",
    }:
        raise ValueError("Service registry must define the four supported profiles")
    for profile, members in registry["profiles"].items():
        if (
            not isinstance(members, list)
            or not members
            or set(members) - known_services
        ):
            raise ValueError(f"Profile {profile!r} has invalid service membership")

    pending = dict(graph)
    while pending:
        ready = {
            key
            for key, dependencies in pending.items()
            if not dependencies & pending.keys()
        }
        if not ready:
            raise ValueError("Service registry dependency graph contains a cycle")
        pending = {
            key: dependencies - ready
            for key, dependencies in pending.items()
            if key not in ready
        }


def load_registry() -> dict[str, Any]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    validate_registry(registry)
    return registry


def container_name(key: str) -> str:
    return key if key.startswith("cml-memoryhive-") else f"cml-memoryhive-{key}"


def local_image(image_key: str, registry: dict[str, Any] | None = None) -> str:
    registry = registry or load_registry()
    return (
        f"{registry['registry'].rstrip('/')}/"
        f"{registry['registry_namespace'].strip('/')}/{image_key}:local"
    )


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
        "CORS_ORIGINS": '${CORS_ORIGINS:-["http://localhost:3000"]}',
        "TEMPORAL_ENABLED": "true" if temporal else "false",
        "TEMPORAL_ADDRESS": "${TEMPORAL_ADDRESS:-temporal:7233}",
        "TEMPORAL_UI_URL": "${TEMPORAL_UI_URL:-http://localhost:8088}",
        "TEMPORAL_NAMESPACE": "${TEMPORAL_NAMESPACE:-default}",
        "TEMPORAL_TASK_QUEUE": "${TEMPORAL_TASK_QUEUE:-memoryhive-analysis}",
        "TEMPORAL_SCHEDULER_POLL_SECONDS": "${TEMPORAL_SCHEDULER_POLL_SECONDS:-10}",
        "TEMPORAL_SCHEDULER_BATCH_SIZE": "${TEMPORAL_SCHEDULER_BATCH_SIZE:-25}",
        "WORKER_METRICS_PORT": "${WORKER_METRICS_PORT:-9101}",
        "TEMPORAL_SDK_METRICS_PORT": "${TEMPORAL_SDK_METRICS_PORT:-9102}",
        "TEMPORAL_SCHEDULER_METRICS_PORT": "${TEMPORAL_SCHEDULER_METRICS_PORT:-9103}",
        "TEMPORAL_WORKER_METRICS_PORT": "${TEMPORAL_WORKER_METRICS_PORT:-9104}",
        "N8N_WEBHOOK_URL": "${N8N_WEBHOOK_URL:-}",
        "N8N_API_KEY": "${N8N_API_KEY:-}",
        "N8N_SIGNING_SECRET": "${N8N_SIGNING_SECRET:-}",
        "N8N_DEPLOYMENT_TYPE": "${N8N_DEPLOYMENT_TYPE:-self_hosted}",
        "OLLAMA_BASE_URL": "${OLLAMA_BASE_URL:-}",
        "OLLAMA_MODEL": "${OLLAMA_MODEL:-qwen2.5:3b}",
        "OLLAMA_EMBEDDING_MODEL": "${OLLAMA_EMBEDDING_MODEL:-}",
        "OLLAMA_KEEP_ALIVE": "${OLLAMA_KEEP_ALIVE:-5m}",
        "OLLAMA_DEPLOYMENT_TYPE": "${OLLAMA_DEPLOYMENT_TYPE:-local}",
        "OPENROUTER_ENABLED": "${OPENROUTER_ENABLED:-false}",
        "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY:-}",
        "OPENROUTER_BASE_URL": "${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}",
        "OPENROUTER_MODEL": "${OPENROUTER_MODEL:-}",
        "OPENROUTER_EMBEDDING_MODEL": "${OPENROUTER_EMBEDDING_MODEL:-}",
        "OPENROUTER_ALLOWED_MODELS": "${OPENROUTER_ALLOWED_MODELS:-[]}",
        "OPENROUTER_ALLOWED_PROVIDERS": "${OPENROUTER_ALLOWED_PROVIDERS:-[]}",
        "OPENROUTER_ALLOW_FALLBACKS": "${OPENROUTER_ALLOW_FALLBACKS:-false}",
        "OPENROUTER_REQUIRE_PARAMETERS": "${OPENROUTER_REQUIRE_PARAMETERS:-true}",
        "OPENROUTER_DATA_COLLECTION": "${OPENROUTER_DATA_COLLECTION:-deny}",
        "HUGGINGFACE_ENABLED": "${HUGGINGFACE_ENABLED:-false}",
        "HUGGINGFACE_TOKEN": "${HUGGINGFACE_TOKEN:-}",
        "HUGGINGFACE_ROUTER_URL": "${HUGGINGFACE_ROUTER_URL:-https://router.huggingface.co}",
        "HUGGINGFACE_HUB_URL": "${HUGGINGFACE_HUB_URL:-https://huggingface.co}",
        "HUGGINGFACE_CHAT_MODEL": "${HUGGINGFACE_CHAT_MODEL:-}",
        "HUGGINGFACE_EMBEDDING_MODEL": "${HUGGINGFACE_EMBEDDING_MODEL:-}",
        "HUGGINGFACE_CHAT_MODELS": "${HUGGINGFACE_CHAT_MODELS:-[]}",
        "HUGGINGFACE_EMBEDDING_MODELS": "${HUGGINGFACE_EMBEDDING_MODELS:-[]}",
        "HUGGINGFACE_VISION_MODELS": "${HUGGINGFACE_VISION_MODELS:-[]}",
        "HUGGINGFACE_ALLOWED_PROVIDERS": "${HUGGINGFACE_ALLOWED_PROVIDERS:-[]}",
        "OPENAI_COMPATIBLE_ENABLED": "${OPENAI_COMPATIBLE_ENABLED:-false}",
        "OPENAI_COMPATIBLE_BASE_URL": "${OPENAI_COMPATIBLE_BASE_URL:-}",
        "OPENAI_COMPATIBLE_API_KEY": "${OPENAI_COMPATIBLE_API_KEY:-}",
        "OPENAI_COMPATIBLE_MODEL": "${OPENAI_COMPATIBLE_MODEL:-}",
        "OPENAI_COMPATIBLE_EMBEDDING_MODEL": "${OPENAI_COMPATIBLE_EMBEDDING_MODEL:-}",
        "OPENAI_COMPATIBLE_ENDPOINT_MODE": "${OPENAI_COMPATIBLE_ENDPOINT_MODE:-chat_completions}",
        "OPENAI_COMPATIBLE_CAPABILITIES": "${OPENAI_COMPATIBLE_CAPABILITIES:-[\"enrichment\",\"model_listing\",\"token_usage\",\"health\"]}",
        "OPENAI_COMPATIBLE_CHAT_MODELS": "${OPENAI_COMPATIBLE_CHAT_MODELS:-[]}",
        "OPENAI_COMPATIBLE_EMBEDDING_MODELS": "${OPENAI_COMPATIBLE_EMBEDDING_MODELS:-[]}",
        "OPENAI_COMPATIBLE_ALLOWED_HOSTS": "${OPENAI_COMPATIBLE_ALLOWED_HOSTS:-[]}",
        "OPENAI_COMPATIBLE_ALLOW_PRIVATE_NETWORK": "${OPENAI_COMPATIBLE_ALLOW_PRIVATE_NETWORK:-false}",
        "OPENAI_COMPATIBLE_PRIVATE_HOSTS": "${OPENAI_COMPATIBLE_PRIVATE_HOSTS:-[]}",
        "OPENAI_COMPATIBLE_EXTRA_HEADERS": "${OPENAI_COMPATIBLE_EXTRA_HEADERS:-{}}",
        "OPENAI_COMPATIBLE_EXTRA_OPTIONS": "${OPENAI_COMPATIBLE_EXTRA_OPTIONS:-{}}",
        "OPENAI_COMPATIBLE_DEPLOYMENT_TYPE": "${OPENAI_COMPATIBLE_DEPLOYMENT_TYPE:-third_party}",
        "AI_ENRICHMENT_ROUTE": "${AI_ENRICHMENT_ROUTE:-}",
        "AI_ENRICHMENT_FALLBACK_ROUTES": "${AI_ENRICHMENT_FALLBACK_ROUTES:-[]}",
        "AI_SUMMARIZATION_ROUTE": "${AI_SUMMARIZATION_ROUTE:-}",
        "AI_SUMMARIZATION_FALLBACK_ROUTES": "${AI_SUMMARIZATION_FALLBACK_ROUTES:-[]}",
        "AI_EMBEDDINGS_ROUTE": "${AI_EMBEDDINGS_ROUTE:-}",
        "AI_EMBEDDINGS_FALLBACK_ROUTES": "${AI_EMBEDDINGS_FALLBACK_ROUTES:-[]}",
        "AI_EMBEDDING_DIMENSIONS": "${AI_EMBEDDING_DIMENSIONS:-768}",
        "AI_EMBEDDING_NORMALIZATION": "${AI_EMBEDDING_NORMALIZATION:-l2}",
        "AI_EMBEDDING_INDEX_VERSION": "${AI_EMBEDDING_INDEX_VERSION:-1}",
        "AI_EMBEDDING_CHUNK_CHARACTERS": "${AI_EMBEDDING_CHUNK_CHARACTERS:-2000}",
        "AI_EMBEDDING_CHUNK_OVERLAP": "${AI_EMBEDDING_CHUNK_OVERLAP:-200}",
        "AI_EMBEDDING_BACKFILL_BATCH_SIZE": "${AI_EMBEDDING_BACKFILL_BATCH_SIZE:-25}",
        "AI_EMBEDDING_BACKFILL_MAX_ITEMS_PER_MINUTE": "${AI_EMBEDDING_BACKFILL_MAX_ITEMS_PER_MINUTE:-30}",
        "AI_RERANKING_ROUTE": "${AI_RERANKING_ROUTE:-}",
        "AI_RERANKING_FALLBACK_ROUTES": "${AI_RERANKING_FALLBACK_ROUTES:-[]}",
        "AI_VISION_ROUTE": "${AI_VISION_ROUTE:-}",
        "AI_VISION_FALLBACK_ROUTES": "${AI_VISION_FALLBACK_ROUTES:-[]}",
        "AI_CROSS_PROVIDER_FALLBACK_ENABLED": "${AI_CROSS_PROVIDER_FALLBACK_ENABLED:-false}",
        "AI_EXTERNAL_CONTENT_ALLOWED": "${AI_EXTERNAL_CONTENT_ALLOWED:-false}",
        "AI_ALLOWED_EXTERNAL_PROVIDERS": "${AI_ALLOWED_EXTERNAL_PROVIDERS:-[]}",
        "AI_DAILY_REQUEST_BUDGET": "${AI_DAILY_REQUEST_BUDGET:-0}",
        "AI_MONTHLY_REQUEST_BUDGET": "${AI_MONTHLY_REQUEST_BUDGET:-0}",
        "AI_DAILY_TOKEN_BUDGET": "${AI_DAILY_TOKEN_BUDGET:-0}",
        "AI_MONTHLY_TOKEN_BUDGET": "${AI_MONTHLY_TOKEN_BUDGET:-0}",
        "AI_DAILY_COST_BUDGET_USD": "${AI_DAILY_COST_BUDGET_USD:-0}",
        "AI_MONTHLY_COST_BUDGET_USD": "${AI_MONTHLY_COST_BUDGET_USD:-0}",
        "AI_PER_USER_DAILY_REQUEST_QUOTA": "${AI_PER_USER_DAILY_REQUEST_QUOTA:-0}",
        "AI_PER_USER_MONTHLY_REQUEST_QUOTA": "${AI_PER_USER_MONTHLY_REQUEST_QUOTA:-0}",
        "AI_PER_USER_DAILY_TOKEN_QUOTA": "${AI_PER_USER_DAILY_TOKEN_QUOTA:-0}",
        "AI_PER_USER_MONTHLY_TOKEN_QUOTA": "${AI_PER_USER_MONTHLY_TOKEN_QUOTA:-0}",
        "AI_SUGGESTION_AUTO_APPLY_THRESHOLD": "${AI_SUGGESTION_AUTO_APPLY_THRESHOLD:-0}",
    }


def depends_on(active: set[str], dependencies: list[str]) -> dict[str, Any]:
    return {
        dependency: {
            "condition": (
                "service_healthy"
                if dependency in {"db", "redis", "minio", "temporal-db"}
                else "service_started"
            )
        }
        for dependency in dependencies
        if dependency in active
    }


def published_ports(descriptor: dict[str, Any]) -> list[str]:
    ports = []
    if descriptor.get("host_port"):
        ports.append(
            f"${{{descriptor['host_port_env']}:-{descriptor['host_port']}}}:"
            f"{descriptor['port']}"
        )
    for port in descriptor.get("additional_ports", []):
        ports.append(
            f"${{{port['host_port_env']}:-{port['host_port']}}}:{port['port']}"
        )
    return ports


def build_service(
    key: str, active: set[str], registry: dict[str, Any] | None = None
) -> dict[str, Any]:
    registry = registry or load_registry()
    descriptor = next(item for item in registry["services"] if item["key"] == key)
    image_descriptor = next(
        (
            item
            for item in registry["images"]
            if item["key"] == descriptor.get("image_key")
        ),
        None,
    )
    temporal_enabled = key.startswith("cml-memoryhive-temporal-")
    backend_env = backend_environment(temporal=temporal_enabled)
    source = f"../../{descriptor.get('source', '')}"
    if key == "db":
        return {
            "container_name": container_name(key),
            "image": descriptor["image"],
            "environment": {
                "POSTGRES_USER": "${POSTGRES_USER:-memoryhive}",
                "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD:-memoryhive123}",
                "POSTGRES_DB": "${POSTGRES_DB:-memoryhive}",
            },
            "ports": published_ports(descriptor),
            "volumes": ["pgdata:/var/lib/postgresql/data"],
            "healthcheck": {
                "test": [
                    "CMD-SHELL",
                    "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}",
                ],
                "interval": "5s",
                "timeout": "5s",
                "retries": 10,
            },
            "restart": "unless-stopped",
        }
    if key == "redis":
        return {
            "container_name": container_name(key),
            "image": descriptor["image"],
            "command": ["redis-server", "--save", "60", "1", "--loglevel", "warning"],
            "ports": published_ports(descriptor),
            "volumes": ["redisdata:/data"],
            "healthcheck": {
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "5s",
                "timeout": "3s",
                "retries": 10,
            },
            "restart": "unless-stopped",
        }
    if key == "minio":
        return {
            "container_name": container_name(key),
            "image": descriptor["image"],
            "command": ["server", "/data", "--console-address", ":9001"],
            "environment": {
                "MINIO_ROOT_USER": "${MINIO_ROOT_USER:-minioadmin}",
                "MINIO_ROOT_PASSWORD": "${MINIO_ROOT_PASSWORD:-minioadmin123}",
            },
            "ports": published_ports(descriptor),
            "volumes": ["miniodata:/data"],
            "healthcheck": {
                "test": [
                    "CMD",
                    "curl",
                    "--fail",
                    "--silent",
                    "http://localhost:9000/minio/health/ready",
                ],
                "interval": "10s",
                "timeout": "5s",
                "retries": 10,
            },
            "restart": "unless-stopped",
        }
    if key == "temporal-db":
        return {
            "container_name": container_name(key),
            "image": descriptor["image"],
            "environment": {
                "POSTGRES_USER": "temporal",
                "POSTGRES_PASSWORD": "temporal",
            },
            "volumes": ["temporal_pgdata:/var/lib/postgresql/data"],
            "healthcheck": {
                "test": ["CMD-SHELL", "pg_isready -U temporal"],
                "interval": "5s",
                "timeout": "5s",
                "retries": 20,
            },
            "restart": "unless-stopped",
        }
    if key == "temporal":
        return {
            "container_name": container_name(key),
            "image": descriptor["image"],
            "environment": {
                "DB": "postgres12",
                "DB_PORT": "5432",
                "POSTGRES_USER": "temporal",
                "POSTGRES_PWD": "temporal",
                "POSTGRES_SEEDS": "temporal-db",
                "DYNAMIC_CONFIG_FILE_PATH": "config/dynamicconfig/development-sql.yaml",
                "PROMETHEUS_ENDPOINT": "0.0.0.0:8000",
            },
            "ports": published_ports(descriptor),
            "volumes": [
                "../../ops/temporal/dynamicconfig:/etc/temporal/config/dynamicconfig:ro"
            ],
            "depends_on": depends_on(active, ["temporal-db"]),
            "restart": "unless-stopped",
        }
    if key == "temporal-ui":
        return {
            "container_name": container_name(key),
            "image": descriptor["image"],
            "environment": {
                "TEMPORAL_ADDRESS": "temporal:7233",
                "TEMPORAL_CORS_ORIGINS": "http://localhost:${FRONTEND_PORT:-3000}",
            },
            "ports": published_ports(descriptor),
            "depends_on": depends_on(active, ["temporal"]),
            "restart": "unless-stopped",
        }
    if key == "prometheus":
        return {
            "container_name": container_name(key),
            "image": descriptor["image"],
            "command": [
                "--config.file=/etc/prometheus/prometheus.yml",
                "--storage.tsdb.retention.time=15d",
                "--web.enable-lifecycle",
            ],
            "ports": published_ports(descriptor),
            "volumes": [
                "../../ops/prometheus.yml:/etc/prometheus/prometheus.yml:ro",
                "../../ops/alerts.yml:/etc/prometheus/alerts.yml:ro",
                "prometheus_data:/prometheus",
            ],
            "depends_on": depends_on(active, descriptor["depends_on"]),
            "restart": "unless-stopped",
        }
    if key == "alertmanager":
        return {
            "container_name": container_name(key),
            "image": descriptor["image"],
            "command": ["--config.file=/etc/alertmanager/alertmanager.yml"],
            "ports": published_ports(descriptor),
            "volumes": [
                "../../ops/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro"
            ],
            "restart": "unless-stopped",
        }
    if key == "grafana":
        return {
            "container_name": container_name(key),
            "image": descriptor["image"],
            "environment": {
                "GF_SECURITY_ADMIN_USER": "${GRAFANA_ADMIN_USER:-admin}",
                "GF_SECURITY_ADMIN_PASSWORD": "${GRAFANA_ADMIN_PASSWORD:-memoryhive-local}",
                "GF_USERS_ALLOW_SIGN_UP": "false",
            },
            "ports": published_ports(descriptor),
            "volumes": [
                "../../ops/grafana/provisioning:/etc/grafana/provisioning:ro",
                "../../ops/grafana/dashboards:/var/lib/grafana/dashboards:ro",
                "grafana_data:/var/lib/grafana",
            ],
            "depends_on": depends_on(active, descriptor["depends_on"]),
            "restart": "unless-stopped",
        }
    if key == "cml-memoryhive-frontend":
        return {
            "container_name": container_name(key),
            "image": local_image(descriptor["image_key"], registry),
            "build": {
                "context": f"../../{descriptor['source']}",
                "dockerfile": image_descriptor["dockerfile"],
                "target": image_descriptor["runtime_target"],
            },
            "command": descriptor["command"],
            "environment": {
                "VITE_API_URL": "${VITE_API_URL:-/api/v1}",
                "VITE_SUPPORT_EMAIL": "${VITE_SUPPORT_EMAIL:-support@memoryhive.example.com}",
                "VITE_PROXY_TARGET": "http://cml-memoryhive-backend:8000",
            },
            "ports": published_ports(descriptor),
            "depends_on": depends_on(active, ["cml-memoryhive-backend"]),
            "volumes": [
                f"../../{descriptor['source']}:/app",
                "frontend_node_modules:/app/node_modules",
            ],
            "healthcheck": {
                "test": [
                    "CMD",
                    "wget",
                    "--quiet",
                    "--output-document=/dev/null",
                    "http://127.0.0.1:3000/",
                ],
                "interval": "10s",
                "timeout": "5s",
                "retries": 10,
            },
            "restart": "unless-stopped",
        }
    service = {
        "container_name": container_name(key),
        "image": local_image(descriptor["image_key"], registry),
        "build": {
            "context": source,
            "dockerfile": image_descriptor["dockerfile"],
            "target": image_descriptor["runtime_target"],
        },
        "command": descriptor["command"],
        "environment": backend_env,
        "depends_on": depends_on(active, descriptor["depends_on"]),
        "volumes": [f"{source}:/app"],
        "restart": "unless-stopped",
    }
    if key == "cml-memoryhive-backend":
        service["ports"] = published_ports(descriptor)
        service["healthcheck"] = {
            "test": [
                "CMD",
                "curl",
                "--fail",
                "--silent",
                "http://localhost:8000/health/ready",
            ],
            "interval": "10s",
            "timeout": "5s",
            "retries": 10,
        }
    else:
        marker = descriptor["health"]["marker"]
        service["healthcheck"] = {
            "test": [
                "CMD",
                "uv",
                "run",
                "--frozen",
                "--no-sync",
                "python",
                "-c",
                f"import pathlib,sys; sys.exit(0 if b'{marker}' in pathlib.Path('/proc/1/cmdline').read_bytes() else 1)",
            ],
            "interval": "15s",
            "timeout": "5s",
            "retries": 3,
        }
    return service


def render_profile(registry: dict[str, Any], profile: str) -> dict[str, Any]:
    active = set(registry["profiles"][profile])
    services = {
        key: build_service(key, active, registry)
        for key in registry["profiles"][profile]
    }
    if "cml-memoryhive-backend" in active:
        backend = next(
            service
            for service in registry["services"]
            if service["key"] == "cml-memoryhive-backend"
        )
        backend_image = next(
            image
            for image in registry["images"]
            if image["key"] == backend["image_key"]
        )
        backend_source = f"../../{backend['source']}"
        services["migrate"] = {
            "container_name": "cml-memoryhive-migrate",
            "image": local_image(backend["image_key"], registry),
            "build": {
                "context": backend_source,
                "dockerfile": backend_image["dockerfile"],
                "target": backend_image["runtime_target"],
            },
            "command": [
                "uv",
                "run",
                "--frozen",
                "--no-sync",
                "alembic",
                "upgrade",
                "head",
            ],
            "environment": backend_environment(temporal=False),
            "depends_on": depends_on(active, ["db"]),
            "volumes": [f"{backend_source}:/app"],
            "restart": "no",
        }
        for key in active:
            if key.startswith("cml-memoryhive-") and key != "cml-memoryhive-frontend":
                services[key].setdefault("depends_on", {})["migrate"] = {
                    "condition": "service_completed_successfully"
                }
    return {
        "name": "cml-memoryhive",
        "services": services,
        "volumes": {
            name: {}
            for name in (
                "pgdata",
                "redisdata",
                "miniodata",
                "temporal_pgdata",
                "frontend_node_modules",
                "prometheus_data",
                "grafana_data",
            )
        },
        "networks": {"default": {"name": "cml-memoryhive-network"}},
    }


def main() -> int:
    registry = load_registry()
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    HEALTH_ROOT.mkdir(parents=True, exist_ok=True)
    services_by_key = {service["key"]: service for service in registry["services"]}
    for profile in registry["profiles"]:
        compose_path = RUNTIME_ROOT / f"docker-compose.{profile}.yml"
        compose_path.write_text(
            json.dumps(render_profile(registry, profile), indent=2) + "\n",
            encoding="utf-8",
        )
        health = {
            "profile": profile,
            "services": {
                key: {
                    "key": key,
                    "kind": services_by_key[key]["kind"],
                    "host": "127.0.0.1",
                    "port": services_by_key[key].get("host_port", 0),
                    "host_port_env": services_by_key[key].get("host_port_env"),
                    "health": services_by_key[key]["health"],
                    "container": container_name(key),
                    "kubernetes": services_by_key[key].get("kubernetes"),
                }
                for key in registry["profiles"][profile]
            },
        }
        (HEALTH_ROOT / f"health-registry.{profile}.json").write_text(
            json.dumps(health, indent=2) + "\n", encoding="utf-8"
        )
    (RUNTIME_ROOT / "docker-compose.yml").write_text(
        (RUNTIME_ROOT / "docker-compose.full.yml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
