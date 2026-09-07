#!/usr/bin/env python3
"""Build Memoryhive service images with the repository image naming convention."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "cml-memoryhive-build" / "service-registry.json"


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def safe_tag(value: str) -> str:
    tag = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip(".-")
    if not tag:
        raise ValueError("Docker tag cannot be empty")
    return tag[:128]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def image_repository(registry: str, namespace: str, image_key: str) -> str:
    return f"{registry.rstrip('/')}/{namespace.strip('/')}/{image_key}".lower()


def build_command(
    image: dict[str, Any],
    *,
    registry: str,
    namespace: str,
    version: str,
    sha: str,
    platforms: str,
    push: bool,
    load: bool,
) -> list[str]:
    repo = image_repository(registry, namespace, image["key"])
    short_sha = sha[:7]
    cmd = [
        "docker",
        "buildx",
        "build",
        str(ROOT / image["context"]),
        "--file",
        str(ROOT / image["context"] / image.get("dockerfile", "Dockerfile")),
        "--target",
        image.get("target", "production"),
        "--tag",
        f"{repo}:{safe_tag(f'{version}-{short_sha}')}",
        "--tag",
        f"{repo}:{safe_tag(version)}",
        "--tag",
        f"{repo}:latest",
    ]
    for key, value in image.get("build_args", {}).items():
        if isinstance(value, str) and value.startswith("$"):
            value = os.getenv(value[1:], "support@memoryhive.example.com")
        cmd.extend(["--build-arg", f"{key}={value}"])
    if push:
        cmd.extend(["--platform", platforms, "--push"])
    elif load:
        cmd.extend(["--platform", platforms.split(",", 1)[0], "--load"])
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", default="all", help="image key from service-registry.json")
    parser.add_argument("--registry")
    parser.add_argument("--namespace")
    parser.add_argument("--version")
    parser.add_argument("--sha")
    parser.add_argument("--platforms")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--load", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config()
    registry = args.registry or os.getenv("REGISTRY") or config["registry"]
    namespace = (
        args.namespace
        or os.getenv("REGISTRY_NAMESPACE")
        or config["registry_namespace"]
    )
    version = args.version or os.getenv("GITHUB_REF_NAME") or git_value(
        "describe", "--tags", "--always"
    )
    sha = args.sha or os.getenv("GITHUB_SHA") or git_value("rev-parse", "HEAD")
    if not version or not sha:
        raise SystemExit("Unable to determine version and git SHA")
    platforms = args.platforms or ",".join(config["platforms"])
    images = [
        image
        for image in config["images"]
        if args.service == "all" or image["key"] == args.service
    ]
    if not images:
        raise SystemExit(f"No image named {args.service!r} in {CONFIG_PATH}")
    for image in images:
        dockerfile = ROOT / image["context"] / image.get("dockerfile", "Dockerfile")
        if not dockerfile.exists():
            raise SystemExit(f"Missing Dockerfile for {image['key']}: {dockerfile}")
        cmd = build_command(
            image,
            registry=registry,
            namespace=namespace,
            version=version,
            sha=sha,
            platforms=platforms,
            push=args.push,
            load=args.load or not args.push,
        )
        print(" ".join(cmd))
        if not args.dry_run:
            subprocess.run(cmd, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
