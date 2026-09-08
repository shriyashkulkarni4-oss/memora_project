#!/usr/bin/env -S uv run
"""Promote immutable build-manifest images into deployment environment pins."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DEPLOYMENTS = Path(__file__).resolve().parents[1]
DEFAULT_PINS = DEPLOYMENTS / "image-versions.json"
OWNED = (
    "cml-memoryhive-backend",
    "cml-memoryhive-worker",
    "cml-memoryhive-temporal-worker",
    "cml-memoryhive-temporal-scheduler",
    "cml-memoryhive-frontend",
)
IMMUTABLE = re.compile(r"^ghcr\.io/coding-monkey-labs-client-projects/cml-memoryhive-(?:backend|frontend):[^:]+-[0-9a-f]{7}$")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def promote(environment: str, pins: dict[str, Any], manifest: dict[str, Any] | None) -> bool:
    if environment == "staging":
        if not manifest or manifest.get("app") != "cml-memoryhive":
            raise ValueError("Staging promotion requires a cml-memoryhive build manifest")
        source = manifest.get("runtime", {})
    elif environment == "production":
        source = pins["staging"]
    else:
        raise ValueError(f"Unsupported promotion environment: {environment}")
    target = pins[environment]
    changed = False
    for key in OWNED:
        image = source.get(key)
        if not image or not IMMUTABLE.fullmatch(image):
            raise ValueError(f"{key} is not pinned to a valid immutable image: {image!r}")
        if target.get(key) != image:
            target[key] = image
            changed = True
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", choices=("staging", "production"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--image-versions", type=Path, default=DEFAULT_PINS)
    args = parser.parse_args()
    if args.environment == "staging" and not args.manifest:
        parser.error("staging promotion requires --manifest")
    pins = read(args.image_versions)
    manifest = read(args.manifest) if args.manifest else None
    changed = promote(args.environment, pins, manifest)
    if changed:
        args.image_versions.write_text(json.dumps(pins, indent=2) + "\n", encoding="utf-8")
        print(f"updated {args.environment} image pins")
    else:
        print(f"{args.environment} image pins already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
