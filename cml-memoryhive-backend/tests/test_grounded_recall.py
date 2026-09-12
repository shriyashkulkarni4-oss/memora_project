"""Grounded recall claim verification, feature gate, and owner isolation."""

import pytest

from app.ai.grounded_recall import (
    GroundedClaim,
    GroundedRecallResult,
    RecallPassage,
    verify_claims,
)
from app.config import Settings
from tests.test_core_api import register_and_login


def test_claim_verifier_rejects_unsupported_content() -> None:
    passages = (
        RecallPassage(
            1,
            "item-1",
            "Temporal",
            "Temporal workflows preserve durable event history.",
        ),
    )
    supported = verify_claims(
        "Temporal workflows preserve durable event history.",
        passages,
        minimum_overlap=0.5,
    )
    assert supported == (
        GroundedClaim("Temporal workflows preserve durable event history.", (1,)),
    )
    assert not verify_claims(
        "Paris is the capital of France.", passages, minimum_overlap=0.2
    )


@pytest.mark.asyncio
async def test_recall_is_disabled_until_evaluation_gate(
    api_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _storage = api_client
    _user, headers = await register_and_login(client, "recall-gate@example.com")
    from app.api.v1 import items as items_api

    monkeypatch.setattr(
        items_api,
        "get_settings",
        lambda: Settings(database_url="sqlite+aiosqlite://"),
    )
    response = await client.post(
        "/api/v1/items/recall", headers=headers, json={"question": "What did I save?"}
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_recall_uses_only_owner_scoped_passages(
    api_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _storage = api_client
    owner, headers = await register_and_login(client, "recall-owner@example.com")
    _other, other_headers = await register_and_login(client, "recall-other@example.com")
    own = await client.post(
        "/api/v1/items",
        headers=headers,
        json={
            "type": "text",
            "title": "Temporal note",
            "raw_text": "Temporal workflows preserve durable event history.",
        },
    )
    foreign = await client.post(
        "/api/v1/items",
        headers=other_headers,
        json={
            "type": "text",
            "title": "Private Temporal note",
            "raw_text": "Temporal contains another user's private secret.",
        },
    )
    assert own.status_code == foreign.status_code == 201

    configured = Settings(
        database_url="sqlite+aiosqlite://",
        ollama_base_url="http://localhost:11434",
        ai_recall_route="ollama:test",
        ai_hybrid_search_enabled=False,
        ai_grounded_recall_enabled=True,
        ai_evaluation_release_gate_passed=True,
    )
    from app.api.v1 import items as items_api

    monkeypatch.setattr(items_api, "get_settings", lambda: configured)

    seen: list[RecallPassage] = []

    async def fake_answer(
        self, question, passages, *, user_id, external_allowed_for_user
    ):
        del self, question
        assert user_id == owner["id"]
        assert external_allowed_for_user is False
        seen.extend(passages)
        return GroundedRecallResult(
            answer="Temporal workflows preserve durable event history. [1]",
            claims=(
                GroundedClaim(
                    "Temporal workflows preserve durable event history.", (1,)
                ),
            ),
            insufficient_evidence=False,
            provider="ollama",
            model="test",
        )

    monkeypatch.setattr(items_api.GroundedRecallPipeline, "answer", fake_answer)
    response = await client.post(
        "/api/v1/items/recall",
        headers=headers,
        json={"question": "Temporal"},
    )
    assert response.status_code == 200
    assert [passage.item_id for passage in seen] == [own.json()["id"]]
    assert response.json()["citations"][0]["item_id"] == own.json()["id"]
    assert foreign.json()["id"] not in response.text
