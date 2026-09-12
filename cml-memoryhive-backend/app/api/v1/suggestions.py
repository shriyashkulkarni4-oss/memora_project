"""Private, reversible AI suggestion review endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import (
    AISuggestionFeedback,
    AISuggestionPreference,
    EnrichmentRecord,
    Item,
    Tag,
)
from app.schemas.common import ErrorResponse
from app.schemas.suggestion import (
    SuggestionDecisionCommand,
    SuggestionDecisionRequest,
    SuggestionOverviewResponse,
    SuggestionResponse,
)

router = APIRouter()
ERRORS = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().lstrip("#").split())


async def _item(db: DbSession, user_id: str, item_id: str) -> Item:
    item = await db.scalar(
        select(Item).where(
            Item.id == item_id, Item.user_id == user_id, Item.deleted_at.is_(None)
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


async def _enrichment(
    db: DbSession, item: Item, analysis_version: int | None = None
) -> EnrichmentRecord:
    version = analysis_version or item.analysis_version
    record = await db.scalar(
        select(EnrichmentRecord).where(
            EnrichmentRecord.item_id == item.id,
            EnrichmentRecord.analysis_version == version,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="AI suggestions are not available")
    return record


async def _overview(
    db: DbSession, item: Item, record: EnrichmentRecord
) -> SuggestionOverviewResponse:
    feedback = list(
        await db.scalars(
            select(AISuggestionFeedback)
            .where(
                AISuggestionFeedback.item_id == item.id,
                AISuggestionFeedback.analysis_version == record.analysis_version,
            )
            .order_by(AISuggestionFeedback.created_at, AISuggestionFeedback.id)
        )
    )
    preferences = set(
        await db.scalars(
            select(AISuggestionPreference.normalized_value).where(
                AISuggestionPreference.user_id == item.user_id,
                AISuggestionPreference.suggestion_type == "tag",
            )
        )
    )
    states: dict[tuple[str, str], tuple[str, bool]] = {}
    for event in feedback:
        key = (event.suggestion_type, event.normalized_value)
        if event.action in {"accept", "auto_accept"}:
            states[key] = ("accepted", True)
        elif event.action == "undo":
            states[key] = ("pending", False)
        elif event.action == "reject":
            states[key] = ("rejected", False)
        elif event.action == "never":
            states[key] = ("never", False)

    candidates = [("tag", value) for value in record.suggested_tags]
    if record.classification:
        candidates.append(("classification", record.classification))
    suggestions = []
    for suggestion_type, value in candidates:
        normalized = _normalize(value)
        if suggestion_type == "tag" and normalized in preferences:
            status, can_undo = "never", False
        else:
            status, can_undo = states.get(
                (suggestion_type, normalized), ("pending", False)
            )
        suggestions.append(
            SuggestionResponse(
                suggestion_type=suggestion_type,
                value=value,
                confidence=record.confidence,
                status=status,
                can_undo=can_undo,
            )
        )
    return SuggestionOverviewResponse(
        item_id=item.id,
        analysis_version=record.analysis_version,
        item_revision=item.revision,
        topics=list(record.topics),
        classification=record.classification,
        suggestions=suggestions,
    )


@router.get(
    "/{item_id}/suggestions",
    response_model=SuggestionOverviewResponse,
    responses=ERRORS,
)
async def get_suggestions(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> SuggestionOverviewResponse:
    item = await _item(db, current_user.id, item_id)
    return await _overview(db, item, await _enrichment(db, item))


async def _tag(db: DbSession, user_id: str, value: str) -> Tag:
    normalized = _normalize(value)[:50]
    tag = await db.scalar(
        select(Tag).where(Tag.user_id == user_id, Tag.name == normalized)
    )
    if tag is None:
        tag = Tag(user_id=user_id, name=normalized, color="#64748b")
        db.add(tag)
        await db.flush()
    return tag


async def _apply_decision(
    db: DbSession,
    item: Item,
    record: EnrichmentRecord,
    command: SuggestionDecisionCommand,
    client_id: str,
) -> bool:
    normalized = _normalize(command.value)
    valid_values = (
        {_normalize(value) for value in record.suggested_tags}
        if command.suggestion_type == "tag"
        else {_normalize(record.classification or "")}
    )
    if normalized not in valid_values:
        raise HTTPException(
            status_code=400, detail="Suggestion is not in this analysis"
        )

    changed = False
    metadata: dict[str, object] = {}
    feedback_id = str(uuid.uuid4())
    if command.action == "accept" and command.suggestion_type == "tag":
        tag = await _tag(db, item.user_id, command.value)
        await db.refresh(item, attribute_names=["tags"])
        was_present = any(existing.id == tag.id for existing in item.tags)
        if not was_present:
            item.tags.append(tag)
            changed = True
            applied = dict((item.item_metadata or {}).get("ai_applied_tags") or {})
            applied[normalized] = feedback_id
            item.item_metadata = {
                **(item.item_metadata or {}),
                "ai_applied_tags": applied,
            }
        metadata = {"tag_id": tag.id, "was_present": was_present}
    elif command.action == "accept":
        organization = dict((item.item_metadata or {}).get("organization") or {})
        if organization.get("ai_classification") != command.value:
            organization["ai_classification"] = command.value
            organization["provenance"] = {
                "enrichment_id": record.id,
                "analysis_version": record.analysis_version,
            }
            item.item_metadata = {
                **(item.item_metadata or {}),
                "organization": organization,
            }
            changed = True
    elif command.action == "never":
        preference = await db.scalar(
            select(AISuggestionPreference).where(
                AISuggestionPreference.user_id == item.user_id,
                AISuggestionPreference.suggestion_type == command.suggestion_type,
                AISuggestionPreference.normalized_value == normalized,
            )
        )
        if preference is None:
            db.add(
                AISuggestionPreference(
                    user_id=item.user_id,
                    suggestion_type=command.suggestion_type,
                    normalized_value=normalized,
                )
            )
    elif command.action == "undo":
        accepted = await db.scalar(
            select(AISuggestionFeedback)
            .where(
                AISuggestionFeedback.item_id == item.id,
                AISuggestionFeedback.analysis_version == record.analysis_version,
                AISuggestionFeedback.suggestion_type == command.suggestion_type,
                AISuggestionFeedback.normalized_value == normalized,
                AISuggestionFeedback.action.in_(("accept", "auto_accept")),
            )
            .order_by(AISuggestionFeedback.created_at.desc())
        )
        if accepted is None:
            raise HTTPException(
                status_code=409, detail="Accepted suggestion was not found"
            )
        if command.suggestion_type == "tag" and accepted.changed_item:
            tag_id = accepted.metadata_json.get("tag_id")
            applied = dict((item.item_metadata or {}).get("ai_applied_tags") or {})
            await db.refresh(item, attribute_names=["tags"])
            original = next((tag for tag in item.tags if tag.id == tag_id), None)
            if original and applied.get(normalized) == accepted.id:
                item.tags.remove(original)
                applied.pop(normalized, None)
                item.item_metadata = {
                    **(item.item_metadata or {}),
                    "ai_applied_tags": applied,
                }
                changed = True
        elif command.suggestion_type == "classification" and accepted.changed_item:
            organization = dict((item.item_metadata or {}).get("organization") or {})
            provenance = organization.get("provenance")
            if (
                isinstance(provenance, dict)
                and provenance.get("enrichment_id") == record.id
            ):
                organization.pop("ai_classification", None)
                organization.pop("provenance", None)
                item.item_metadata = {
                    **(item.item_metadata or {}),
                    "organization": organization,
                }
                changed = True

    decisions = dict((item.item_metadata or {}).get("suggestion_decisions") or {})
    decisions[f"{command.suggestion_type}:{normalized}"] = command.action
    item.item_metadata = {
        **(item.item_metadata or {}),
        "suggestion_decisions": decisions,
    }

    db.add(
        AISuggestionFeedback(
            id=feedback_id,
            client_id=client_id,
            user_id=item.user_id,
            item_id=item.id,
            enrichment_id=record.id,
            analysis_version=record.analysis_version,
            suggestion_type=command.suggestion_type,
            value=command.value,
            normalized_value=normalized,
            action=command.action,
            changed_item=changed,
            item_revision_after=item.revision + 1,
            metadata_json=metadata,
        )
    )
    return changed


@router.post(
    "/{item_id}/suggestions/decisions",
    response_model=SuggestionOverviewResponse,
    responses=ERRORS,
)
async def decide_suggestions(
    item_id: str,
    data: SuggestionDecisionRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuggestionOverviewResponse:
    item = await _item(db, current_user.id, item_id)
    existing = await db.scalar(
        select(AISuggestionFeedback).where(
            AISuggestionFeedback.client_id == f"{data.client_id}:0"
        )
    )
    if existing:
        return await _overview(
            db, item, await _enrichment(db, item, data.analysis_version)
        )
    if item.revision != data.expected_revision:
        raise HTTPException(status_code=409, detail="Item revision conflict")
    record = await _enrichment(db, item, data.analysis_version)
    changed = False
    for index, command in enumerate(data.decisions):
        changed = (
            await _apply_decision(
                db, item, record, command, f"{data.client_id}:{index}"
            )
            or changed
        )
    item.revision += 1
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return await _overview(db, item, record)
