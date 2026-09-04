"""End-to-end core API behavior and ownership tests."""

import base64
import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import FakeStorage

PASSWORD = "correct-horse-battery"
pytestmark = pytest.mark.asyncio
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


async def register_and_login(
    client: AsyncClient, email: str
) -> tuple[dict[str, str], dict[str, str]]:
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": "Test User"},
    )
    assert registration.status_code == 201, registration.text
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    tokens = login.json()
    return registration.json(), {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_authentication_session_lifecycle(
    api_client: tuple[AsyncClient, FakeStorage],
) -> None:
    client, _storage = api_client
    email = "Owner@Example.com"
    user = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": " Owner "},
    )
    assert user.status_code == 201
    assert user.json()["email"] == "owner@example.com"
    assert user.json()["name"] == "Owner"

    duplicate = await client.post(
        "/api/v1/auth/register",
        json={"email": email.lower(), "password": PASSWORD},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CONFLICT"

    weak = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert weak.status_code == 422

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email.upper(), "password": PASSWORD},
    )
    assert login.status_code == 200
    first_tokens = login.json()
    headers = {"Authorization": f"Bearer {first_tokens['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["id"] == user.json()["id"]

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    second_tokens = refresh.json()
    assert second_tokens["refresh_token"] != first_tokens["refresh_token"]

    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_tokens["refresh_token"]},
    )
    assert replay.status_code == 401

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": second_tokens["refresh_token"]},
    )
    assert logout.status_code == 204
    after_logout = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_tokens["refresh_token"]},
    )
    assert after_logout.status_code == 401


async def test_complete_item_workflow_and_ownership(
    api_client: tuple[AsyncClient, FakeStorage],
) -> None:
    client, storage = api_client
    _owner, owner_headers = await register_and_login(client, "owner@example.com")
    _other, other_headers = await register_and_login(client, "other@example.com")

    category = await client.post(
        "/api/v1/categories",
        json={"name": "Research", "color": "#2563eb"},
        headers=owner_headers,
    )
    assert category.status_code == 201, category.text
    category_id = category.json()["id"]

    item_id = str(uuid.uuid4())
    created = await client.post(
        "/api/v1/items",
        json={
            "id": item_id,
            "type": "link",
            "url": "https://example.com/useful?ref=test",
            "title": "Useful research",
            "source": "article",
            "category_id": category_id,
            "tags": ["Reading", "research"],
        },
        headers=owner_headers,
    )
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["id"] == item_id
    assert item["source_domain"] == "example.com"
    assert {tag["name"] for tag in item["tags"]} == {"reading", "research"}
    assert item["revision"] == 1

    text_item = await client.post(
        "/api/v1/items",
        json={"type": "text", "raw_text": "An offline thought", "tags": ["research"]},
        headers=owner_headers,
    )
    assert text_item.status_code == 201
    assert text_item.json()["processing_status"] == "ready"

    first_page = await client.get(
        "/api/v1/items", params={"limit": 1}, headers=owner_headers
    )
    assert first_page.status_code == 200
    assert first_page.json()["has_more"] is True
    second_page = await client.get(
        "/api/v1/items",
        params={"limit": 1, "cursor": first_page.json()["next_cursor"]},
        headers=owner_headers,
    )
    assert second_page.status_code == 200
    assert second_page.json()["items"][0]["id"] != first_page.json()["items"][0]["id"]

    tagged = await client.get(
        "/api/v1/items", params={"tag": "reading"}, headers=owner_headers
    )
    assert [record["id"] for record in tagged.json()["items"]] == [item_id]

    favorite = await client.put(
        f"/api/v1/items/{item_id}/favorite", headers=owner_headers
    )
    assert favorite.status_code == 200
    assert favorite.json()["is_favorite"] is True
    revision = favorite.json()["revision"]

    conflict = await client.patch(
        f"/api/v1/items/{item_id}",
        json={"expected_revision": 1, "title": "Stale update"},
        headers=owner_headers,
    )
    assert conflict.status_code == 409
    updated = await client.patch(
        f"/api/v1/items/{item_id}",
        json={"expected_revision": revision, "title": "Updated title"},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated title"

    cross_user_get = await client.get(f"/api/v1/items/{item_id}", headers=other_headers)
    assert cross_user_get.status_code == 404
    foreign_category = await client.post(
        "/api/v1/items",
        json={
            "type": "link",
            "url": "https://other.example.com",
            "category_id": category_id,
        },
        headers=other_headers,
    )
    assert foreign_category.status_code == 400

    invalid_image = await client.post(
        "/api/v1/items/screenshot",
        files={"file": ("fake.png", b"not an image", "image/png")},
        headers=owner_headers,
    )
    assert invalid_image.status_code == 415
    assert invalid_image.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"

    screenshot = await client.post(
        "/api/v1/items/screenshot",
        data={"title": "Captured screen", "tags": "visual,research"},
        files={"file": ("capture.png", PNG_1X1, "image/png")},
        headers=owner_headers,
    )
    assert screenshot.status_code == 201, screenshot.text
    screenshot_body = screenshot.json()
    assert screenshot_body["type"] == "screenshot"
    assert screenshot_body["assets"][0]["width"] == 1
    asset_id = screenshot_body["assets"][0]["id"]

    download = await client.get(
        f"/api/v1/assets/{asset_id}/download",
        headers=owner_headers,
        follow_redirects=False,
    )
    assert download.status_code == 307
    assert download.headers["location"].startswith("https://assets.example.test/")
    denied_download = await client.get(
        f"/api/v1/assets/{asset_id}/download", headers=other_headers
    )
    assert denied_download.status_code == 404
    assert storage.objects

    archived = await client.put(
        f"/api/v1/items/{item_id}/archive", headers=owner_headers
    )
    assert archived.json()["is_archived"] is True
    active_ids = {
        record["id"]
        for record in (await client.get("/api/v1/items", headers=owner_headers)).json()[
            "items"
        ]
    }
    assert item_id not in active_ids
    restored = await client.delete(
        f"/api/v1/items/{item_id}/archive", headers=owner_headers
    )
    assert restored.json()["is_archived"] is False

    stats = await client.get("/api/v1/items/stats", headers=owner_headers)
    assert stats.status_code == 200
    assert stats.json()["total_items"] == 3
    assert stats.json()["by_type"] == {"link": 1, "screenshot": 1, "text": 1}

    tags = await client.get("/api/v1/tags", headers=owner_headers)
    assert tags.status_code == 200
    assert {tag["name"] for tag in tags.json()} == {"reading", "research", "visual"}
    assert (await client.get("/api/v1/tags", headers=other_headers)).json() == []

    deleted = await client.delete(f"/api/v1/items/{item_id}", headers=owner_headers)
    assert deleted.status_code == 204
    assert (
        await client.get(f"/api/v1/items/{item_id}", headers=owner_headers)
    ).status_code == 404
