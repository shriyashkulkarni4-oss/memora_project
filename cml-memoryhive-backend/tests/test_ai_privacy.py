"""External AI consent defaults, mutation, and portable export."""

import io
import json
import zipfile

import pytest

from tests.test_core_api import register_and_login

pytestmark = pytest.mark.asyncio


async def test_external_ai_consent_defaults_off_and_is_exported(api_client) -> None:
    client, _storage = api_client
    user, headers = await register_and_login(client, "ai-privacy@example.com")
    assert user["ai_external_processing_allowed"] is False

    updated = await client.patch(
        "/api/v1/auth/ai-privacy",
        headers=headers,
        json={"external_processing_allowed": True},
    )
    assert updated.status_code == 200
    assert updated.json()["ai_external_processing_allowed"] is True
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["ai_external_processing_allowed"] is True

    exported = await client.get("/api/v1/account/export", headers=headers)
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        manifest = json.loads(archive.read("memoryhive-export.json"))
    assert manifest["user"]["ai_external_processing_allowed"] is True
