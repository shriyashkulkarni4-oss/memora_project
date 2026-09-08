#!/usr/bin/env -S uv run
"""Reject obsolete active project paths and first-party artifact names."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", ".expo", ".pytest_cache", "node_modules", "__pycache__", "GOAL-1", "archieves", "presentations"}
SKIP_NAMES = {"package-lock.json", "IMPLEMENTATION_PLAN.md", "audit_project_naming.py"}
TEXT_SUFFIXES = {"", ".json", ".md", ".mjs", ".py", ".sh", ".toml", ".ts", ".tsx", ".yml", ".yaml"}
PATTERNS = (
    re.compile(r"cml-memora"),
    re.compile(r"\bdirectory:\s+/(backend|frontend|mobile|automation|build|k8s|health_checker)\b"),
    re.compile(r"\bworking-directory:\s+(backend|frontend|mobile|automation)\b"),
    re.compile(r"\bnpm --prefix (frontend|mobile|automation)\b"),
    re.compile(r"\bscope=(backend|frontend|mobile|automation)\b"),
    re.compile(r"(?<!cml-)\bmemoryhive-(backend|frontend)(?=[:/])"),
)
OLD_PATH = re.compile(r"(?<![A-Za-z0-9_/-])(backend|frontend|mobile|automation|build|k8s|health_checker)/")


def files() -> list[Path]:
    selected = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name in SKIP_NAMES or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        selected.append(path)
    return selected


def main() -> int:
    obsolete_dirs = [name for name in ("backend", "frontend", "mobile", "automation", "build", "k8s", "health_checker") if (ROOT / name).exists()]
    violations = [f"obsolete top-level directory: {name}" for name in obsolete_dirs]
    for path in files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            path_violation = "cml-memoryhive-build" not in path.parts and OLD_PATH.search(line)
            if path_violation or any(pattern.search(line) for pattern in PATTERNS):
                violations.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
    if violations:
        print("Active project naming audit failed:")
        print("\n".join(violations))
        return 1
    print("Active project naming audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
