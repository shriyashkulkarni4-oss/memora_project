"""Admin persona and user-management API tests."""

import base64
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.models import Item, ProcessingJob, ProcessingStatus
from tests.conftest import FakeStorage

PASSWORD = "correct-horse-battery"
pytestmark = pytest.mark.asyncio
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


async def register_and_login(
    client: AsyncClient, email: str
) -> tuple[dict[str, object], dict[str, str]]:
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": email.split("@")[0]},
    )
    assert registration.status_code == 201, registration.text
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    return registration.json(), {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


async def test_admin_persona_manages_user_access_and_deletion(
    api_client: tuple[AsyncClient, FakeStorage],
) -> None:
    client, storage = api_client
    admin, admin_headers = await register_and_login(client, "admin@example.com")
    user, user_headers = await register_and_login(client, "member@example.com")

    assert admin["role"] == "admin"
    assert user["role"] == "user"
    assert (
        await client.get("/api/v1/admin/dashboard", headers=user_headers)
    ).status_code == 403

    screenshot = await client.post(
        "/api/v1/items/screenshot",
        data={"title": "Managed user asset", "tags": "admin-test"},
        files={"file": ("capture.png", PNG_1X1, "image/png")},
        headers=user_headers,
    )
    assert screenshot.status_code == 201, screenshot.text

    dashboard = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    dashboard_body = dashboard.json()
    assert dashboard_body["users_total"] == 2
    assert dashboard_body["active_users"] == 2
    assert dashboard_body["admin_users"] == 1
    assert dashboard_body["items_total"] == 1
    assert dashboard_body["assets_total"] == 1
    assert dashboard_body["processing_pending"] == 1

    users = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert users.status_code == 200
    managed = next(
        record for record in users.json()["users"] if record["id"] == user["id"]
    )
    assert managed["item_count"] == 1
    assert managed["asset_count"] == 1
    assert managed["storage_bytes"] > 0

    self_disable = await client.patch(
        f"/api/v1/admin/users/{admin['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert self_disable.status_code == 400

    disabled = await client.patch(
        f"/api/v1/admin/users/{user['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert (
        await client.get("/api/v1/auth/me", headers=user_headers)
    ).status_code == 401
    blocked_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": PASSWORD},
    )
    assert blocked_login.status_code == 401

    enabled = await client.patch(
        f"/api/v1/admin/users/{user['id']}",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert enabled.status_code == 200
    assert enabled.json()["is_active"] is True

    deleted = await client.delete(
        f"/api/v1/admin/users/{user['id']}", headers=admin_headers
    )
    assert deleted.status_code == 204
    assert storage.deleted
    remaining = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert {record["id"] for record in remaining.json()["users"]} == {admin["id"]}


async def test_admin_backup_status_is_fail_closed(
    api_client: tuple[AsyncClient, FakeStorage],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, _storage = api_client
    _admin, admin_headers = await register_and_login(client, "backup-admin@example.com")
    monkeypatch.setenv("BACKUP_ROOT", str(tmp_path / "backups"))
    monkeypatch.delenv("ADMIN_BACKUP_COMMAND", raising=False)
    get_settings.cache_clear()


async def test_admin_processing_queue_lists_and_retries_failed_jobs(
    api_client_with_db: tuple[
        AsyncClient, FakeStorage, async_sessionmaker[AsyncSession]
    ],
) -> None:
    client, _storage, session_factory = api_client_with_db
    _admin, admin_headers = await register_and_login(client, "queue-admin@example.com")
    _user, user_headers = await register_and_login(client, "queue-user@example.com")

    captured = await client.post(
        "/api/v1/items",
        json={
            "type": "link",
            "url": "https://example.com/retry-me",
            "title": "Retry Me",
        },
        headers=user_headers,
    )
    assert captured.status_code == 201, captured.text
    item_id = captured.json()["id"]

    async with session_factory() as session:
        job = await session.scalar(
            select(ProcessingJob).where(ProcessingJob.item_id == item_id)
        )
        item = await session.get(Item, item_id)
        assert job and item
        job.status = "failed"
        job.attempts = job.max_attempts
        job.last_error = "metadata fetch timed out"
        item.processing_status = ProcessingStatus.FAILED
        item.processing_error = job.last_error
        await session.commit()

    forbidden = await client.get("/api/v1/admin/processing/jobs", headers=user_headers)
    assert forbidden.status_code == 403

    failed_jobs = await client.get(
        "/api/v1/admin/processing/jobs?status=failed", headers=admin_headers
    )
    assert failed_jobs.status_code == 200, failed_jobs.text
    body = failed_jobs.json()
    assert body["total"] == 1
    record = body["jobs"][0]
    assert record["item_id"] == item_id
    assert record["item_title"] == "Retry Me"
    assert record["item_type"] == "link"
    assert record["item_processing_status"] == "failed"
    assert record["user_email"] == "queue-user@example.com"
    assert record["last_error"] == "metadata fetch timed out"

    retried = await client.post(
        f"/api/v1/admin/processing/jobs/{record['id']}/retry",
        headers=admin_headers,
    )
    assert retried.status_code == 200, retried.text
    retry_body = retried.json()
    assert retry_body["item_id"] == item_id
    assert retry_body["status"] == "pending"
    assert retry_body["attempts"] == 0

    duplicate = await client.post(
        f"/api/v1/admin/processing/jobs/{record['id']}/retry",
        headers=admin_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["message"] == "Item processing is already queued"

    status_response = await client.get("/api/v1/admin/backup", headers=admin_headers)
    assert status_response.status_code == 200
    assert status_response.json()["configured"] is False
    assert status_response.json()["recent"] == []

    run_response = await client.post("/api/v1/admin/backup/run", headers=admin_headers)
    assert run_response.status_code == 503
    get_settings.cache_clear()


async def test_admin_can_run_configured_backup_command(
    api_client: tuple[AsyncClient, FakeStorage],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, _storage = api_client
    _admin, admin_headers = await register_and_login(client, "ops-admin@example.com")
    backup_root = tmp_path / "backups"
    command = tmp_path / "backup.sh"
    command.write_text(
        "\n".join(
            [
                "#!/usr/bin/env sh",
                "set -eu",
                'DEST="$BACKUP_ROOT/20260906T000000Z"',
                'mkdir -p "$DEST/minio"',
                'printf dump > "$DEST/postgres.dump"',
                'printf sums > "$DEST/SHA256SUMS"',
                'printf "%s\\n" "$DEST"',
            ]
        ),
        encoding="utf-8",
    )
    command.chmod(0o755)
    monkeypatch.setenv("BACKUP_ROOT", str(backup_root))
    monkeypatch.setenv("ADMIN_BACKUP_COMMAND", str(command))
    get_settings.cache_clear()

    run_response = await client.post("/api/v1/admin/backup/run", headers=admin_headers)
    assert run_response.status_code == 200, run_response.text
    body = run_response.json()
    assert body["status"] == "succeeded"
    assert body["latest"]["has_postgres_dump"] is True
    assert body["latest"]["has_minio_dir"] is True
    assert body["latest"]["has_checksums"] is True

    status_response = await client.get("/api/v1/admin/backup", headers=admin_headers)
    assert status_response.status_code == 200
    assert status_response.json()["latest"]["path"].endswith("20260906T000000Z")
    get_settings.cache_clear()
