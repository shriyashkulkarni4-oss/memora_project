"""Password change and session invalidation tests."""

import pytest
from httpx import AsyncClient

from tests.conftest import FakeStorage

PASSWORD = "correct-horse-battery"
NEW_PASSWORD = "new-correct-horse-battery"
pytestmark = pytest.mark.asyncio


async def test_change_password_revokes_refresh_and_invalidates_access_tokens(
    api_client: tuple[AsyncClient, FakeStorage],
) -> None:
    client, _storage = api_client
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "password@example.com",
            "password": PASSWORD,
            "name": "Password User",
        },
    )
    assert registration.status_code == 201, registration.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "password@example.com", "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    same_password = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": PASSWORD},
        headers=headers,
    )
    assert same_password.status_code == 400

    changed = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        headers=headers,
    )
    assert changed.status_code == 204

    stale_access = await client.get("/api/v1/auth/me", headers=headers)
    assert stale_access.status_code == 401
    stale_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert stale_refresh.status_code == 401
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "password@example.com", "password": PASSWORD},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "password@example.com", "password": NEW_PASSWORD},
    )
    assert new_login.status_code == 200
    new_me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_login.json()['access_token']}"},
    )
    assert new_me.status_code == 200
