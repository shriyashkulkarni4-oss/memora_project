#!/usr/bin/env -S uv run
"""Generate the image-version handoff artifact consumed by deployments."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "cml-memoryhive-build" / "service-registry.json"
DEFAULT_OUTPUT = ROOT / "cml-memoryhive-build" / "build" / "output" / "image-versions.json"


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def safe_tag(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    normalized = normalized.strip(".-")
    if not normalized:
        raise ValueError("Docker tag cannot be empty")
    return normalized[:128]


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("images"):
        raise ValueError(f"{path} must define at least one image")
    return data


def image_repository(registry: str, namespace: str, image_key: str) -> str:
    return f"{registry.rstrip('/')}/{namespace.strip('/')}/{image_key}".lower()


def build_manifest(
    config: dict[str, Any],
    *,
    registry: str,
    namespace: str,
    version: str,
    git_sha: str,
    created_at: str,
) -> dict[str, Any]:
    short_sha = git_sha[:7]
    immutable_tag = safe_tag(f"{version}-{short_sha}")
    release_tag = safe_tag(version)
    images: dict[str, dict[str, str]] = {}
    for image in config["images"]:
        repo = image_repository(registry, namespace, image["key"])
        images[image["key"]] = {
            "repository": repo,
            "immutable": f"{repo}:{immutable_tag}",
            "release": f"{repo}:{release_tag}",
            "latest": f"{repo}:latest",
        }

    runtime = {
        service["key"]: images[service["image_key"]]["immutable"]
        for service in config["services"]
        if service.get("image_key")
    }
    return {
        "schema_version": 1,
        "app": config["app"],
        "version": release_tag,
        "git_sha": git_sha,
        "short_sha": short_sha,
        "created_at": created_at,
        "registry": registry,
        "namespace": namespace,
        "images": images,
        "runtime": runtime,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--registry")
    parser.add_argument("--namespace")
    parser.add_argument("--version")
    parser.add_argument("--sha")
    parser.add_argument("--created-at")
    args = parser.parse_args()

    config = load_config(args.config)
    registry = args.registry or os.getenv("REGISTRY") or config["registry"]
    namespace = (
        args.namespace
        or os.getenv("REGISTRY_NAMESPACE")
        or config["registry_namespace"]
    )
    version = args.version or os.getenv("GITHUB_REF_NAME") or git_value(
        "describe", "--tags", "--always"
    )
    git_sha = args.sha or os.getenv("GITHUB_SHA") or git_value("rev-parse", "HEAD")
    if not version or not git_sha:
        raise SystemExit("Unable to determine version and git SHA")
    created_at = args.created_at or os.getenv("BUILD_CREATED_AT")
    if not created_at:
        epoch = os.getenv("SOURCE_DATE_EPOCH")
        created_at = (
            datetime.fromtimestamp(int(epoch), timezone.utc)
            if epoch
            else datetime.now(timezone.utc)
        ).isoformat().replace("+00:00", "Z")

    manifest = build_manifest(
        config,
        registry=registry,
        namespace=namespace,
        version=version,
        git_sha=git_sha,
        created_at=created_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
