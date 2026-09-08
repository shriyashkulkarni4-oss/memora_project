#!/usr/bin/env -S uv run
"""Render and operate Memoryhive Kubernetes manifests."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from string import Template
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - validation falls back to text checks.
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
K8S_ROOT = ROOT / "cml-memoryhive-deployments"
ENVIRONMENTS = K8S_ROOT / "config" / "environments.json"
PROFILES = K8S_ROOT / "config" / "profiles.json"
IMAGE_VERSIONS = K8S_ROOT / "image-versions.json"
GENERATED = K8S_ROOT / "generated"
TEMPLATES = K8S_ROOT / "templates"
APP = "cml-memoryhive"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def yaml_lines(value: Any, indent: int = 0) -> list[str]:
    space = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            if isinstance(child, (dict, list)) and child:
                lines.append(f"{space}{key}:")
                lines.extend(yaml_lines(child, indent + 2))
            elif isinstance(child, list):
                lines.append(f"{space}{key}: []")
            elif isinstance(child, dict):
                lines.append(f"{space}{key}: {{}}")
            else:
                lines.append(f"{space}{key}: {yaml_scalar(child)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                keys = list(item)
                first = keys[0]
                first_value = item[first]
                if isinstance(first_value, (dict, list)) and first_value:
                    lines.append(f"{space}- {first}:")
                    lines.extend(yaml_lines(first_value, indent + 4))
                else:
                    lines.append(f"{space}- {first}: {yaml_scalar(first_value)}")
                for key in keys[1:]:
                    child = item[key]
                    if isinstance(child, (dict, list)) and child:
                        lines.append(f"{space}  {key}:")
                        lines.extend(yaml_lines(child, indent + 4))
                    elif isinstance(child, list):
                        lines.append(f"{space}  {key}: []")
                    elif isinstance(child, dict):
                        lines.append(f"{space}  {key}: {{}}")
                    else:
                        lines.append(f"{space}  {key}: {yaml_scalar(child)}")
            else:
                lines.append(f"{space}- {yaml_scalar(item)}")
        return lines
    return [f"{space}{yaml_scalar(value)}"]


def to_yaml(resources: list[dict[str, Any]]) -> str:
    return (
        "\n---\n".join("\n".join(yaml_lines(resource)) for resource in resources) + "\n"
    )


def render_template(name: str, values: dict[str, str], allowed: set[str]) -> str:
    template = Template((TEMPLATES / name).read_text(encoding="utf-8"))
    identifiers = set(template.get_identifiers())
    if identifiers - allowed:
        raise ValueError(f"{name} uses disallowed placeholders: {sorted(identifiers - allowed)}")
    missing = identifiers - values.keys()
    if missing:
        raise ValueError(f"{name} is missing values for: {sorted(missing)}")
    rendered = template.substitute(values)
    if re.search(r"\$\{[A-Z][A-Z0-9_]*\}", rendered):
        raise ValueError(f"{name} left unresolved placeholders")
    return rendered


def labels(component: str) -> dict[str, str]:
    return {"app.kubernetes.io/name": APP, "app.kubernetes.io/component": component}


def selector(component: str) -> dict[str, Any]:
    return {"matchLabels": labels(component)}


def metadata(name: str, component: str, namespace: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"name": name, "labels": labels(component)}
    if namespace:
        value["namespace"] = namespace
    return value


def service(
    env: dict[str, Any], name: str, component: str, port: int, target_port: int | str
) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": metadata(name, component, env["namespace"]),
        "spec": {
            "type": env["service_type"],
            "selector": labels(component),
            "ports": [
                {
                    "name": "http" if port in {80, 8000, 9000} else "tcp",
                    "port": port,
                    "targetPort": target_port,
                }
            ],
        },
    }


def env_from(component: str) -> list[dict[str, Any]]:
    return [
        {"configMapRef": {"name": f"{component}-config"}},
        {"secretRef": {"name": f"{component}-secrets"}},
    ]


def app_config(
    env_name: str, env: dict[str, Any], *, temporal_enabled: bool
) -> dict[str, str]:
    domain = env["domain"]
    runtime_env = env_name if env_name in {"staging", "production"} else "development"
    return {
        "ENVIRONMENT": runtime_env,
        "APP_DEBUG": "false",
        "MINIO_BUCKET": "memoryhive-uploads",
        "MINIO_SECURE": "false",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15" if runtime_env == "production" else "1440",
        "REFRESH_TOKEN_EXPIRE_DAYS": "30",
        "CORS_ORIGINS": json.dumps([f"https://{domain}"]),
        "ALLOWED_HOSTS": json.dumps([domain]),
        "RATE_LIMIT_PER_MINUTE": "120",
        "AUTH_RATE_LIMIT_PER_MINUTE": "10",
        "BACKUP_ROOT": "/backups",
        "BACKUP_RETENTION_DAYS": "14",
        "OLLAMA_MODEL": "qwen2.5:3b",
        "TEMPORAL_ENABLED": "true" if temporal_enabled else "false",
        "TEMPORAL_ADDRESS": env["temporal_address"],
        "TEMPORAL_NAMESPACE": "default",
        "TEMPORAL_TASK_QUEUE": "memoryhive-analysis",
        "TEMPORAL_SCHEDULER_POLL_SECONDS": "10",
        "TEMPORAL_SCHEDULER_BATCH_SIZE": "25",
    }


def namespace_resources(env: dict[str, Any]) -> list[dict[str, Any]]:
    namespace = env["namespace"]
    return [
        {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": namespace, "labels": {"app.kubernetes.io/name": APP}},
        },
        {
            "apiVersion": "v1",
            "kind": "ResourceQuota",
            "metadata": {"name": "cml-memoryhive-quota", "namespace": namespace},
            "spec": {
                "hard": {
                    "pods": "40",
                    "requests.cpu": "8",
                    "requests.memory": "16Gi",
                    "limits.cpu": "16",
                    "limits.memory": "32Gi",
                }
            },
        },
        {
            "apiVersion": "v1",
            "kind": "LimitRange",
            "metadata": {"name": "cml-memoryhive-defaults", "namespace": namespace},
            "spec": {
                "limits": [
                    {
                        "type": "Container",
                        "defaultRequest": {"cpu": "100m", "memory": "128Mi"},
                        "default": {"cpu": "500m", "memory": "512Mi"},
                    }
                ]
            },
        },
    ]


def config_resources(
    env_name: str,
    env: dict[str, Any],
    services: set[str],
    *,
    temporal_enabled: bool,
) -> list[dict[str, Any]]:
    namespace = env["namespace"]
    resources: list[dict[str, Any]] = []
    for component in sorted(service for service in services if service.startswith(APP)):
        resources.extend(
            [
                {
                    "apiVersion": "v1",
                    "kind": "ConfigMap",
                    "metadata": {"name": f"{component}-config", "namespace": namespace},
                    "data": app_config(env_name, env, temporal_enabled=temporal_enabled),
                },
                {
                    "apiVersion": "v1",
                    "kind": "ServiceAccount",
                    "metadata": {"name": component, "namespace": namespace},
                    "automountServiceAccountToken": False,
                },
            ]
        )
    return resources


def postgres_resources(env: dict[str, Any], image: str) -> list[dict[str, Any]]:
    storage = env["storage"]["postgres"]
    return [
        service(env, "db", "db", 5432, 5432),
        {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": metadata("db", "db", env["namespace"]),
            "spec": {
                "serviceName": "db",
                "replicas": 1,
                "selector": selector("db"),
                "template": {
                    "metadata": {"labels": labels("db")},
                    "spec": {
                        "containers": [
                            {
                                "name": "postgres",
                                "image": image,
                                "ports": [{"name": "postgres", "containerPort": 5432}],
                                "env": [
                                    {
                                        "name": "POSTGRES_USER",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "cml-memoryhive-infra-secrets",
                                                "key": "POSTGRES_USER",
                                            }
                                        },
                                    },
                                    {
                                        "name": "POSTGRES_PASSWORD",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "cml-memoryhive-infra-secrets",
                                                "key": "POSTGRES_PASSWORD",
                                            }
                                        },
                                    },
                                    {
                                        "name": "POSTGRES_DB",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "cml-memoryhive-infra-secrets",
                                                "key": "POSTGRES_DB",
                                            }
                                        },
                                    },
                                ],
                                "readinessProbe": {
                                    "exec": {
                                        "command": [
                                            "sh",
                                            "-c",
                                            'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
                                        ]
                                    },
                                    "periodSeconds": 10,
                                },
                                "volumeMounts": [
                                    {
                                        "name": "pgdata",
                                        "mountPath": "/var/lib/postgresql/data",
                                    }
                                ],
                            }
                        ]
                    },
                },
                "volumeClaimTemplates": [
                    {
                        "metadata": {"name": "pgdata"},
                        "spec": {
                            "accessModes": ["ReadWriteOnce"],
                            "resources": {"requests": {"storage": storage}},
                        },
                    }
                ],
            },
        },
    ]


def redis_resources(env: dict[str, Any], image: str) -> list[dict[str, Any]]:
    return [
        service(env, "redis", "redis", 6379, 6379),
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": metadata("redis", "redis", env["namespace"]),
            "spec": {
                "replicas": 1,
                "selector": selector("redis"),
                "template": {
                    "metadata": {"labels": labels("redis")},
                    "spec": {
                        "containers": [
                            {
                                "name": "redis",
                                "image": image,
                                "command": [
                                    "redis-server",
                                    "--save",
                                    "60",
                                    "1",
                                    "--loglevel",
                                    "warning",
                                ],
                                "ports": [{"name": "redis", "containerPort": 6379}],
                                "readinessProbe": {
                                    "exec": {"command": ["redis-cli", "ping"]},
                                    "periodSeconds": 10,
                                },
                                "volumeMounts": [
                                    {"name": "redisdata", "mountPath": "/data"}
                                ],
                            }
                        ],
                        "volumes": [{"name": "redisdata", "emptyDir": {}}],
                    },
                },
            },
        },
    ]


def minio_resources(env: dict[str, Any], image: str) -> list[dict[str, Any]]:
    storage = env["storage"]["minio"]
    return [
        service(env, "minio", "minio", 9000, 9000),
        {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": metadata("minio", "minio", env["namespace"]),
            "spec": {
                "serviceName": "minio",
                "replicas": 1,
                "selector": selector("minio"),
                "template": {
                    "metadata": {"labels": labels("minio")},
                    "spec": {
                        "containers": [
                            {
                                "name": "minio",
                                "image": image,
                                "command": ["minio", "server", "/data"],
                                "ports": [{"name": "http", "containerPort": 9000}],
                                "env": [
                                    {
                                        "name": "MINIO_ROOT_USER",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "cml-memoryhive-infra-secrets",
                                                "key": "MINIO_ROOT_USER",
                                            }
                                        },
                                    },
                                    {
                                        "name": "MINIO_ROOT_PASSWORD",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "cml-memoryhive-infra-secrets",
                                                "key": "MINIO_ROOT_PASSWORD",
                                            }
                                        },
                                    },
                                ],
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": "/minio/health/ready",
                                        "port": "http",
                                    },
                                    "periodSeconds": 15,
                                },
                                "volumeMounts": [
                                    {"name": "miniodata", "mountPath": "/data"}
                                ],
                            }
                        ]
                    },
                },
                "volumeClaimTemplates": [
                    {
                        "metadata": {"name": "miniodata"},
                        "spec": {
                            "accessModes": ["ReadWriteOnce"],
                            "resources": {"requests": {"storage": storage}},
                        },
                    }
                ],
            },
        },
    ]


def app_deployment(
    name: str,
    component: str,
    image: str,
    env: dict[str, Any],
    command: list[str] | None,
    port: int | None,
) -> dict[str, Any]:
    container: dict[str, Any] = {
        "name": component,
        "image": image,
        "imagePullPolicy": env["image_pull_policy"],
        "envFrom": env_from(component),
        "resources": env["resources"][component],
    }
    if command:
        container["command"] = command
    if port:
        container["ports"] = [{"name": "http", "containerPort": port}]
    if component == "cml-memoryhive-backend":
        container["readinessProbe"] = {
            "httpGet": {
                "path": "/health/ready",
                "port": "http",
                "httpHeaders": [{"name": "Host", "value": env["domain"]}],
            },
            "periodSeconds": 10,
            "failureThreshold": 6,
        }
        container["livenessProbe"] = {
            "httpGet": {
                "path": "/health/live",
                "port": "http",
                "httpHeaders": [{"name": "Host", "value": env["domain"]}],
            },
            "periodSeconds": 30,
        }
    elif component == "cml-memoryhive-frontend":
        container["readinessProbe"] = {
            "httpGet": {"path": "/", "port": "http"},
            "periodSeconds": 10,
        }
        container["livenessProbe"] = {
            "httpGet": {"path": "/", "port": "http"},
            "periodSeconds": 30,
        }
    elif component == "cml-memoryhive-worker":
        container["livenessProbe"] = {
            "exec": {
                "command": [
                    "uv",
                    "run",
                    "--frozen",
                    "--no-sync",
                    "python",
                    "-c",
                    "import pathlib,sys; sys.exit(0 if b'app.worker' in pathlib.Path('/proc/1/cmdline').read_bytes() else 1)",
                ]
            },
            "periodSeconds": 30,
        }
    elif component in {"cml-memoryhive-temporal-worker", "cml-memoryhive-temporal-scheduler"}:
        module = (
            "app.temporal_pipeline.worker"
            if component == "cml-memoryhive-temporal-worker"
            else "app.temporal_pipeline.scheduler"
        )
        container["livenessProbe"] = {
            "exec": {
                "command": [
                    "uv",
                    "run",
                    "--frozen",
                    "--no-sync",
                    "python",
                    "-c",
                    f"import pathlib,sys; sys.exit(0 if b'{module}' in pathlib.Path('/proc/1/cmdline').read_bytes() else 1)",
                ]
            },
            "periodSeconds": 30,
        }
    spec: dict[str, Any] = {
        "replicas": env["replicas"].get(component, 1),
        "selector": selector(component),
        "template": {
            "metadata": {"labels": labels(component)},
            "spec": {"serviceAccountName": component, "automountServiceAccountToken": False, "containers": [container]},
        },
    }
    if component == "cml-memoryhive-backend":
        spec["template"]["spec"]["initContainers"] = [
            {
                "name": "migrate",
                "image": image,
                "imagePullPolicy": env["image_pull_policy"],
                "command": ["uv", "run", "--frozen", "--no-sync", "alembic", "upgrade", "head"],
                "envFrom": env_from(component),
            }
        ]
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": metadata(name, component, env["namespace"]),
        "spec": spec,
    }


def app_resources(
    env: dict[str, Any], images: dict[str, str], services: set[str]
) -> list[tuple[str, list[dict[str, Any]]]]:
    files: list[tuple[str, list[dict[str, Any]]]] = []
    if "cml-memoryhive-backend" in services:
        files.append(
            (
                "30-backend.yaml",
                [
                    service(env, "cml-memoryhive-backend", "cml-memoryhive-backend", 8000, "http"),
                    app_deployment(
                        "cml-memoryhive-backend",
                        "cml-memoryhive-backend",
                        images["cml-memoryhive-backend"],
                        env,
                        [
                            "uv",
                            "run",
                            "--frozen",
                            "--no-sync",
                            "uvicorn",
                            "app.main:app",
                            "--host",
                            "0.0.0.0",
                            "--port",
                            "8000",
                            "--workers",
                            "2",
                            "--proxy-headers",
                            "--forwarded-allow-ips=*",
                        ],
                        8000,
                    ),
                ],
            )
        )
    if "cml-memoryhive-worker" in services:
        files.append(
            (
                "31-worker.yaml",
                [
                    app_deployment(
                        "cml-memoryhive-worker",
                        "cml-memoryhive-worker",
                        images["cml-memoryhive-worker"],
                        env,
                        ["uv", "run", "--frozen", "--no-sync", "python", "-m", "app.worker"],
                        None,
                    )
                ],
            )
        )
    if "cml-memoryhive-temporal-worker" in services:
        files.append(
            (
                "33-temporal-worker.yaml",
                [
                    app_deployment(
                        "cml-memoryhive-temporal-worker",
                        "cml-memoryhive-temporal-worker",
                        images["cml-memoryhive-temporal-worker"],
                        env,
                        ["uv", "run", "--frozen", "--no-sync", "python", "-m", "app.temporal_pipeline.worker"],
                        None,
                    )
                ],
            )
        )
    if "cml-memoryhive-temporal-scheduler" in services:
        files.append(
            (
                "34-temporal-scheduler.yaml",
                [
                    app_deployment(
                        "cml-memoryhive-temporal-scheduler",
                        "cml-memoryhive-temporal-scheduler",
                        images["cml-memoryhive-temporal-scheduler"],
                        env,
                        ["uv", "run", "--frozen", "--no-sync", "python", "-m", "app.temporal_pipeline.scheduler"],
                        None,
                    )
                ],
            )
        )
    if "cml-memoryhive-frontend" in services:
        files.append(
            (
                "32-frontend.yaml",
                [
                    service(env, "cml-memoryhive-frontend", "cml-memoryhive-frontend", 80, "http"),
                    app_deployment(
                        "cml-memoryhive-frontend", "cml-memoryhive-frontend", images["cml-memoryhive-frontend"], env, None, 80
                    ),
                ],
            )
        )
    return files


def ingress_resource(env: dict[str, Any], services: set[str]) -> list[dict[str, Any]]:
    if not {"cml-memoryhive-backend", "cml-memoryhive-frontend"}.issubset(services):
        return []
    return [
        {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": "cml-memoryhive",
                "namespace": env["namespace"],
                "annotations": {
                    "cert-manager.io/cluster-issuer": env["cluster_issuer"]
                },
            },
            "spec": {
                "ingressClassName": env["ingress_class_name"],
                "tls": [{"hosts": [env["domain"]], "secretName": "cml-memoryhive-tls"}],
                "rules": [
                    {
                        "host": env["domain"],
                        "http": {
                            "paths": [
                                {
                                    "path": "/api/v1",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": "cml-memoryhive-backend",
                                            "port": {"number": 8000},
                                        }
                                    },
                                },
                                {
                                    "path": "/health",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": "cml-memoryhive-backend",
                                            "port": {"number": 8000},
                                        }
                                    },
                                },
                                {
                                    "path": "/",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": "cml-memoryhive-frontend",
                                            "port": {"number": 80},
                                        }
                                    },
                                },
                            ]
                        },
                    }
                ],
            },
        }
    ]


def network_policies(
    env: dict[str, Any], services: set[str]
) -> list[dict[str, Any]]:
    resources = [
        {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": "cml-memoryhive-default-deny-ingress",
                "namespace": env["namespace"],
            },
            "spec": {"podSelector": {}, "policyTypes": ["Ingress"]},
        },
        {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": "cml-memoryhive-allow-same-namespace-ingress",
                "namespace": env["namespace"],
            },
            "spec": {
                "podSelector": {},
                "policyTypes": ["Ingress"],
                "ingress": [{"from": [{"podSelector": {}}]}],
            },
        },
    ]
    ingress_components = sorted(
        {"cml-memoryhive-backend", "cml-memoryhive-frontend"} & services
    )
    if ingress_components:
        resources.append(
            {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "NetworkPolicy",
                "metadata": {
                    "name": "cml-memoryhive-allow-ingress-controller",
                    "namespace": env["namespace"],
                },
                "spec": {
                    "podSelector": {
                        "matchExpressions": [
                            {
                                "key": "app.kubernetes.io/component",
                                "operator": "In",
                                "values": ingress_components,
                            }
                        ]
                    },
                    "policyTypes": ["Ingress"],
                    "ingress": [
                        {
                            "from": [
                                {
                                    "namespaceSelector": {
                                        "matchLabels": {
                                            "kubernetes.io/metadata.name": "ingress-nginx"
                                        }
                                    }
                                }
                            ],
                            "ports": [
                                {"protocol": "TCP", "port": 80},
                                {"protocol": "TCP", "port": 8000},
                            ],
                        }
                    ],
                },
            }
        )
    return resources


def load_context(
    env_name: str, profile_name: str | None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    environments = read_json(ENVIRONMENTS)
    profiles = read_json(PROFILES)
    images_by_env = read_json(IMAGE_VERSIONS)
    if env_name not in environments:
        raise SystemExit(f"Unknown environment {env_name!r}")
    env = environments[env_name]
    profile_key = profile_name or env["default_profile"]
    if profile_key not in profiles:
        raise SystemExit(f"Unknown profile {profile_key!r}")
    if env_name not in images_by_env:
        raise SystemExit(f"Missing image versions for {env_name!r}")
    return env, profiles[profile_key], images_by_env[env_name]


def output_dir(base: Path, env_name: str, profile_name: str) -> Path:
    return base / env_name / profile_name


def render(env_name: str, profile_name: str | None, base: Path) -> Path:
    env, profile, images = load_context(env_name, profile_name)
    profile_key = profile_name or env["default_profile"]
    services = set(profile["services"])
    temporal_enabled = bool({"cml-memoryhive-temporal-worker", "cml-memoryhive-temporal-scheduler"} & services)
    out = output_dir(base, env_name, profile_key)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    files: list[tuple[str, list[dict[str, Any]]]] = [
        ("00-namespace.yaml", namespace_resources(env)),
        (
            "10-config.yaml",
            config_resources(
                env_name,
                env,
                services,
                temporal_enabled=temporal_enabled,
            ),
        ),
    ]
    if "db" in services:
        files.append(("20-db.yaml", postgres_resources(env, images["postgres"])))
    if "redis" in services:
        files.append(("21-redis.yaml", redis_resources(env, images["redis"])))
    if "minio" in services:
        files.append(("22-minio.yaml", minio_resources(env, images["minio"])))
    files.extend(app_resources(env, images, services))
    if profile.get("include_ingress"):
        ingress = ingress_resource(env, services)
        if ingress:
            files.append(("40-ingress.yaml", ingress))
    if profile.get("include_network_policies"):
        files.append(("50-network-policy.yaml", network_policies(env, services)))

    files = [(filename, resources) for filename, resources in files if resources]
    documents = "\n---\n".join(
        to_yaml(resources).rstrip()
        for _filename, resources in files
    )
    bundle = render_template(
        "manifest.yaml.tpl",
        {
            "APP": APP,
            "ENVIRONMENT": env_name,
            "PROFILE": profile_key,
            "RESOURCES": documents,
        },
        {"APP", "ENVIRONMENT", "PROFILE", "RESOURCES"},
    )
    (out / "cml-memoryhive.yaml").write_text(bundle.rstrip() + "\n", encoding="utf-8")
    return out


def validate_directory(out: Path) -> None:
    files = sorted(out.glob("*.yaml"))
    if not files:
        raise SystemExit(f"No manifests rendered in {out}")
    for path in files:
        text = path.read_text(encoding="utf-8")
        if re.search(r"\$\{[A-Z][A-Z0-9_]*\}", text):
            raise SystemExit(f"{path} contains unresolved template placeholders")
        if re.search(r"^kind:\s+[\"']?Secret[\"']?\s*$", text, re.MULTILINE):
            raise SystemExit(f"{path} must not persist Secret resources")
        if yaml is not None:
            for document in yaml.safe_load_all(text):
                if not isinstance(document, dict):
                    raise SystemExit(f"{path} rendered a non-object manifest")
                for key in ("apiVersion", "kind", "metadata"):
                    if key not in document:
                        raise SystemExit(f"{path} is missing {key}")
                if not document.get("metadata", {}).get("name"):
                    raise SystemExit(f"{path} is missing metadata.name")
        else:
            for part in [part.strip() for part in text.split("---") if part.strip()]:
                missing = [
                    key
                    for key in ("apiVersion:", "kind:", "metadata:")
                    if key not in part
                ]
                if missing:
                    raise SystemExit(f"{path} is missing {', '.join(missing)}")


def kubectl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["kubectl", *args], cwd=ROOT, text=True, check=check)


def current_context() -> str | None:
    if not shutil.which("kubectl"):
        return None
    try:
        return subprocess.check_output(
            ["kubectl", "config", "current-context"], text=True
        ).strip()
    except subprocess.CalledProcessError:
        return None


def require_context(env: dict[str, Any], skip: bool) -> None:
    if skip:
        return
    expected = env.get("expected_context")
    actual = current_context()
    if actual != expected:
        raise SystemExit(
            f"Refusing cluster mutation: kubectl context is {actual!r}, expected {expected!r}"
        )


def secret_values(env_name: str, profile: dict[str, Any], env_file: Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if env_file:
        if not env_file.is_file():
            raise SystemExit(f"Secret env file not found: {env_file}")
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
    values.update({key: value for key, value in os.environ.items() if value})
    local_defaults = {
        "POSTGRES_USER": "memoryhive",
        "POSTGRES_PASSWORD": "memoryhive123",
        "POSTGRES_DB": "memoryhive",
        "MINIO_ROOT_USER": "minioadmin",
        "MINIO_ROOT_PASSWORD": "minioadmin123",
        "DATABASE_URL": "postgresql+asyncpg://memoryhive:memoryhive123@db:5432/memoryhive",
        "REDIS_URL": "redis://redis:6379/0",
        "MINIO_ENDPOINT": "minio:9000",
        "MINIO_ACCESS_KEY": "minioadmin",
        "MINIO_SECRET_KEY": "minioadmin123",
        "JWT_SECRET_KEY": "dev-secret-key-change-before-production",
        "ENCRYPTION_KEY": "dev-encryption-key-32-bytes-long!",
    }
    if env_name == "local":
        for key, value in local_defaults.items():
            values.setdefault(key, value)
    required: set[str] = set()
    services = set(profile["services"])
    if {"db", "minio"} & services:
        required.update({"POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"})
    if any(service.startswith(APP) for service in services):
        required.update({"DATABASE_URL", "REDIS_URL", "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "JWT_SECRET_KEY", "ENCRYPTION_KEY"})
    invalid = []
    forbidden = ("replace", "change-me", "example", "dev-secret", "memoryhive123", "minioadmin123")
    for key in sorted(required):
        value = values.get(key, "")
        if not value or (env_name != "local" and any(token in value.lower() for token in forbidden)):
            invalid.append(key)
    if invalid:
        raise SystemExit(f"Missing or placeholder secret values for {env_name}: {', '.join(invalid)}")
    return values


def secret_resources(env: dict[str, Any], profile: dict[str, Any], values: dict[str, str]) -> list[dict[str, Any]]:
    namespace = env["namespace"]
    services = set(profile["services"])
    resources: list[dict[str, Any]] = []
    if {"db", "minio"} & services:
        resources.append(
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "cml-memoryhive-infra-secrets", "namespace": namespace},
                "type": "Opaque",
                "stringData": {key: values[key] for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD")},
            }
        )
    app_keys = ("DATABASE_URL", "REDIS_URL", "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "JWT_SECRET_KEY", "ENCRYPTION_KEY", "N8N_WEBHOOK_URL", "N8N_API_KEY", "OLLAMA_BASE_URL", "ADMIN_BOOTSTRAP_EMAILS")
    for component in sorted(service for service in services if service.startswith(APP)):
        resources.append(
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": f"{component}-secrets", "namespace": namespace},
                "type": "Opaque",
                "stringData": {key: values.get(key, "") for key in app_keys},
            }
        )
    return resources


def apply_secrets(env_name: str, env: dict[str, Any], profile: dict[str, Any], env_file: Path | None) -> None:
    payload = to_yaml(secret_resources(env, profile, secret_values(env_name, profile, env_file)))
    subprocess.run(["kubectl", "apply", "-f", "-"], cwd=ROOT, text=True, input=payload, check=True)


def cmd_generate(args: argparse.Namespace) -> int:
    out = render(args.environment, args.profile, args.output)
    print(out)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    out = render(args.environment, args.profile, args.output)
    validate_directory(out)
    if args.kubectl_dry_run and shutil.which("kubectl"):
        kubectl("apply", "--dry-run=client", "-f", str(out))
    print(f"validated {out}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    env, profile, _images = load_context(args.environment, args.profile)
    require_context(env, args.skip_context_check)
    out = render(args.environment, args.profile, args.output)
    apply_secrets(args.environment, env, profile, args.secret_env_file)
    kubectl("apply", "-f", str(out / "cml-memoryhive.yaml"))
    return 0


def deployment_image(namespace: str, deployment: str) -> str | None:
    if not shutil.which("kubectl"):
        return None
    command = [
        "kubectl",
        "-n",
        namespace,
        "get",
        "deployment",
        deployment,
        "-o",
        "jsonpath={.spec.template.spec.containers[0].image}",
    ]
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None


def cmd_upgrade(args: argparse.Namespace) -> int:
    env, profile, images = load_context(args.environment, args.profile)
    require_context(env, args.skip_context_check)
    profile_key = args.profile or env["default_profile"]
    out = render(args.environment, profile_key, args.output)
    deployments = (
        "cml-memoryhive-backend",
        "cml-memoryhive-worker",
        "cml-memoryhive-frontend",
        "cml-memoryhive-temporal-worker",
        "cml-memoryhive-temporal-scheduler",
    )
    changed: list[str] = []
    for name in deployments:
        if name not in profile["services"]:
            continue
        target = images[name]
        current = deployment_image(env["namespace"], name)
        if current == target:
            print(f"{name}: already running {target}")
            continue
        changed.append(name)
    apply_secrets(args.environment, env, profile, args.secret_env_file)
    kubectl("apply", "-f", str(out / "cml-memoryhive.yaml"))
    for name in changed:
        kubectl(
            "-n",
            env["namespace"],
            "rollout",
            "status",
            f"deployment/{name}",
            "--timeout",
            args.timeout,
        )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    env, _profile, _images = load_context(args.environment, args.profile)
    require_context(env, args.skip_context_check)
    kubectl("-n", env["namespace"], "get", "pods,svc,ingress")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    env, _profile, _images = load_context(args.environment, args.profile)
    require_context(env, args.skip_context_check)
    kubectl("-n", env["namespace"], "rollout", "undo", f"deployment/{args.deployment}")
    kubectl(
        "-n",
        env["namespace"],
        "rollout",
        "status",
        f"deployment/{args.deployment}",
        "--timeout",
        args.timeout,
    )
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    env, _profile, _images = load_context(args.environment, args.profile)
    require_context(env, args.skip_context_check)
    if os.getenv("CONFIRM_DELETE") != APP:
        raise SystemExit(f"Set CONFIRM_DELETE={APP} before deleting {env['namespace']}")
    kubectl("delete", "namespace", env["namespace"])
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--output", type=Path, default=GENERATED)
    subcommands = root.add_subparsers(dest="command", required=True)

    def add_env_profile(command: argparse.ArgumentParser) -> None:
        command.add_argument("environment", choices=sorted(read_json(ENVIRONMENTS)))
        command.add_argument("profile", nargs="?", default=None)
        command.add_argument("--skip-context-check", action="store_true")
        command.add_argument("--secret-env-file", type=Path)

    generate = subcommands.add_parser("generate")
    add_env_profile(generate)
    generate.set_defaults(func=cmd_generate)

    validate = subcommands.add_parser("validate")
    add_env_profile(validate)
    validate.add_argument("--kubectl-dry-run", action="store_true")
    validate.set_defaults(func=cmd_validate)

    apply = subcommands.add_parser("apply")
    add_env_profile(apply)
    apply.set_defaults(func=cmd_apply)

    upgrade = subcommands.add_parser("upgrade")
    add_env_profile(upgrade)
    upgrade.add_argument("--timeout", default="180s")
    upgrade.set_defaults(func=cmd_upgrade)

    status = subcommands.add_parser("status")
    add_env_profile(status)
    status.set_defaults(func=cmd_status)

    rollback = subcommands.add_parser("rollback")
    add_env_profile(rollback)
    rollback.add_argument(
        "deployment",
        choices=[
            "cml-memoryhive-backend",
            "cml-memoryhive-worker",
            "cml-memoryhive-frontend",
            "cml-memoryhive-temporal-worker",
            "cml-memoryhive-temporal-scheduler",
        ],
    )
    rollback.add_argument("--timeout", default="180s")
    rollback.set_defaults(func=cmd_rollback)

    delete = subcommands.add_parser("delete")
    add_env_profile(delete)
    delete.set_defaults(func=cmd_delete)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
