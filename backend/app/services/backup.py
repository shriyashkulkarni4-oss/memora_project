"""Admin-facing backup status and command execution helpers."""

import asyncio
import os
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings


class BackupNotConfiguredError(RuntimeError):
    """Raised when an admin tries to run backups without an allowlisted command."""


class BackupCommandError(RuntimeError):
    """Raised when the configured backup command fails."""

    def __init__(self, message: str, *, exit_code: int, stdout: str, stderr: str):
        super().__init__(message)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class BackupCommandTimeoutError(RuntimeError):
    """Raised when the configured backup command exceeds its timeout."""


@dataclass(frozen=True)
class BackupRecord:
    path: str
    created_at: datetime
    size_bytes: int
    has_postgres_dump: bool
    has_minio_dir: bool
    has_checksums: bool


@dataclass(frozen=True)
class BackupStatus:
    configured: bool
    command: str | None
    backup_root: str
    retention_days: int
    recent: list[BackupRecord]

    @property
    def latest(self) -> BackupRecord | None:
        return self.recent[0] if self.recent else None


@dataclass(frozen=True)
class BackupRunResult:
    exit_code: int
    stdout: str
    stderr: str
    latest: BackupRecord | None
    duration_seconds: float


def _created_at(path: Path) -> datetime:
    try:
        return datetime.strptime(path.name, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _directory_size(path: Path) -> int:
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def list_backups(root: str | Path, limit: int = 5) -> list[BackupRecord]:
    backup_root = Path(root).expanduser()
    if not backup_root.exists():
        return []

    records: list[BackupRecord] = []
    for entry in backup_root.iterdir():
        if not entry.is_dir():
            continue
        records.append(
            BackupRecord(
                path=str(entry),
                created_at=_created_at(entry),
                size_bytes=_directory_size(entry),
                has_postgres_dump=(entry / "postgres.dump").is_file(),
                has_minio_dir=(entry / "minio").is_dir(),
                has_checksums=(entry / "SHA256SUMS").is_file(),
            )
        )
    return sorted(records, key=lambda record: record.created_at, reverse=True)[:limit]


def backup_status(settings: Settings) -> BackupStatus:
    command = (
        settings.admin_backup_command.strip() if settings.admin_backup_command else None
    )
    return BackupStatus(
        configured=bool(command),
        command=command,
        backup_root=settings.backup_root,
        retention_days=settings.backup_retention_days,
        recent=list_backups(settings.backup_root),
    )


def _tail(value: bytes, limit: int = 4000) -> str:
    return value.decode("utf-8", errors="replace")[-limit:]


async def run_backup(settings: Settings) -> BackupRunResult:
    command = (
        settings.admin_backup_command.strip() if settings.admin_backup_command else ""
    )
    if not command:
        raise BackupNotConfiguredError("Admin backup command is not configured")

    args = shlex.split(command)
    if not args:
        raise BackupNotConfiguredError("Admin backup command is not configured")

    started = datetime.now(timezone.utc)
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=settings.admin_backup_working_dir or None,
        env=os.environ.copy(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=settings.admin_backup_timeout_seconds,
        )
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise BackupCommandTimeoutError("Backup command timed out") from exc

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    stdout_text = _tail(stdout)
    stderr_text = _tail(stderr)
    if process.returncode != 0:
        raise BackupCommandError(
            "Backup command failed",
            exit_code=process.returncode or 1,
            stdout=stdout_text,
            stderr=stderr_text,
        )

    return BackupRunResult(
        exit_code=process.returncode or 0,
        stdout=stdout_text,
        stderr=stderr_text,
        latest=backup_status(settings).latest,
        duration_seconds=duration,
    )
