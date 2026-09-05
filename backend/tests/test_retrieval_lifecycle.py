"""Search, deduplication, export, and account deletion behavior."""

import base64
import io
import json
import zipfile

import pytest
from httpx import AsyncClient

from tests.conftest import FakeStorage
from tests.test_core_api import PASSWORD, register_and_login

pytestmark = pytest.mark.asyncio
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


async def test_search_and_normalized_url_deduplication(
    api_client: tuple[AsyncClient, FakeStorage],
) -> None:
    client, _storage = api_client
    _user, headers = await register_and_login(client, "search@example.com")

    first = await client.post(
        "/api/v1/items",
        json={
            "type": "link",
            "url": "HTTPS://Example.COM:443/research/?utm_source=newsletter&b=2&a=1#top",
            "title": "Distributed consistency patterns",
            "description": "Coordination strategies for resilient services",
            "tags": ["Architecture"],
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text
    duplicate = await client.post(
        "/api/v1/items",
        json={
            "type": "link",
            "url": "https://example.com/research?a=1&b=2",
        },
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["message"] == "This link is already saved"

    text = await client.post(
        "/api/v1/items",
        json={"type": "text", "raw_text": "A note about vector clocks"},
        headers=headers,
    )
    assert text.status_code == 201

    title_search = await client.get(
        "/api/v1/items", params={"q": "consistency"}, headers=headers
    )
    assert [item["id"] for item in title_search.json()["items"]] == [first.json()["id"]]
    body_search = await client.get(
        "/api/v1/items", params={"q": "vector clocks"}, headers=headers
    )
    assert [item["id"] for item in body_search.json()["items"]] == [text.json()["id"]]
    tag_search = await client.get(
        "/api/v1/items", params={"q": "architecture"}, headers=headers
    )
    assert [item["id"] for item in tag_search.json()["items"]] == [first.json()["id"]]


async def test_portable_export_and_account_deletion(
    api_client: tuple[AsyncClient, FakeStorage],
) -> None:
    client, storage = api_client
    user, headers = await register_and_login(client, "privacy@example.com")
    screenshot = await client.post(
        "/api/v1/items/screenshot",
        data={"title": "Exported capture", "tags": "private,visual"},
        files={"file": ("capture.png", PNG_1X1, "image/png")},
        headers=headers,
    )
    assert screenshot.status_code == 201
    asset = screenshot.json()["assets"][0]

    exported = await client.get("/api/v1/account/export", headers=headers)
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        manifest = json.loads(archive.read("memoryhive-export.json"))
        assert manifest["format"] == "memoryhive-export-v1"
        assert manifest["user"]["id"] == user["id"]
        assert manifest["items"][0]["title"] == "Exported capture"
        assert archive.read(f"assets/{asset['id']}.png") == PNG_1X1

    rejected = await client.request(
        "DELETE",
        "/api/v1/account",
        json={"password": "incorrect-password", "confirmation": "DELETE"},
        headers=headers,
    )
    assert rejected.status_code == 400
    deleted = await client.request(
        "DELETE",
        "/api/v1/account",
        json={"password": PASSWORD, "confirmation": "DELETE"},
        headers=headers,
    )
    assert deleted.status_code == 204, deleted.text
    assert storage.objects == {}
    assert storage.deleted
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "privacy@example.com", "password": PASSWORD},
    )
    assert login.status_code == 401


async def test_change_feed_includes_tombstones_and_stable_pages(
    api_client: tuple[AsyncClient, FakeStorage],
) -> None:
    client, _storage = api_client
    _user, headers = await register_and_login(client, "sync@example.com")
    _other, other_headers = await register_and_login(client, "sync-other@example.com")
    records = []
    for title in ("First offline item", "Second offline item"):
        response = await client.post(
            "/api/v1/items",
            json={"type": "text", "title": title, "raw_text": title},
            headers=headers,
        )
        records.append(response.json())
    await client.delete(f"/api/v1/items/{records[0]['id']}", headers=headers)

    first = await client.get(
        "/api/v1/items/changes", params={"limit": 1}, headers=headers
    )
    assert first.status_code == 200
    assert first.json()["has_more"] is True
    second = await client.get(
        "/api/v1/items/changes",
        params={"limit": 1, "cursor": first.json()["next_cursor"]},
        headers=headers,
    )
    changes = first.json()["items"] + second.json()["items"]
    assert {item["id"] for item in changes} == {item["id"] for item in records}
    tombstone = next(item for item in changes if item["id"] == records[0]["id"])
    assert tombstone["deleted_at"] is not None
    assert (await client.get("/api/v1/items/changes", headers=other_headers)).json()[
        "items"
    ] == []
