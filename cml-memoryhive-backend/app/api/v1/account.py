"""Portable export and durable account deletion endpoints."""

import io
import json
import os
import zipfile
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.items import _response
from app.core.deps import CurrentUser, DbSession
from app.core.security import verify_password
from app.models import (
    AIFieldProvenance,
    AIRun,
    AISuggestionFeedback,
    AISuggestionPreference,
    Category,
    DocumentChunk,
    EnrichmentRecord,
    Item,
    ItemEmbedding,
    Tag,
)
from app.schemas.account import AccountDeleteRequest
from app.schemas.common import ErrorResponse
from app.services.account_lifecycle import delete_user_account
from app.services.storage import StorageService, get_storage_service

router = APIRouter()
Storage = Annotated[StorageService, Depends(get_storage_service)]
ERRORS = {400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}}


@router.get("/export", responses=ERRORS)
async def export_account(
    current_user: CurrentUser, db: DbSession, storage: Storage
) -> StreamingResponse:
    items = list(
        (
            await db.scalars(
                select(Item)
                .options(selectinload(Item.tags), selectinload(Item.assets))
                .where(Item.user_id == current_user.id)
                .order_by(Item.created_at)
            )
        ).unique()
    )
    categories = list(
        await db.scalars(select(Category).where(Category.user_id == current_user.id))
    )
    tags = list(await db.scalars(select(Tag).where(Tag.user_id == current_user.id)))
    ai_runs = list(
        await db.scalars(
            select(AIRun)
            .where(AIRun.user_id == current_user.id)
            .order_by(AIRun.started_at)
        )
    )
    field_provenance = list(
        await db.scalars(
            select(AIFieldProvenance).where(
                AIFieldProvenance.user_id == current_user.id
            )
        )
    )
    embeddings = list(
        await db.scalars(
            select(ItemEmbedding).where(ItemEmbedding.user_id == current_user.id)
        )
    )
    chunks = list(
        await db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.user_id == current_user.id)
            .order_by(
                DocumentChunk.item_id,
                DocumentChunk.analysis_version,
                DocumentChunk.ordinal,
            )
        )
    )
    enrichments = list(
        await db.scalars(
            select(EnrichmentRecord)
            .where(EnrichmentRecord.user_id == current_user.id)
            .order_by(EnrichmentRecord.generated_at)
        )
    )
    suggestion_feedback = list(
        await db.scalars(
            select(AISuggestionFeedback)
            .where(AISuggestionFeedback.user_id == current_user.id)
            .order_by(AISuggestionFeedback.created_at)
        )
    )
    suggestion_preferences = list(
        await db.scalars(
            select(AISuggestionPreference).where(
                AISuggestionPreference.user_id == current_user.id
            )
        )
    )
    manifest = {
        "format": "memoryhive-export-v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "created_at": current_user.created_at.isoformat(),
        },
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "color": category.color,
                "icon": category.icon,
                "description": category.description,
            }
            for category in categories
        ],
        "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in tags],
        "items": [_response(item).model_dump(mode="json") for item in items],
        "ai_runs": [
            {
                "id": run.id,
                "item_id": run.item_id,
                "analysis_version": run.analysis_version,
                "correlation_id": run.correlation_id,
                "task": run.task,
                "provider": run.provider,
                "requested_model": run.requested_model,
                "resolved_model": run.resolved_model,
                "prompt_version": run.prompt_version,
                "schema_version": run.schema_version,
                "content_hash": run.content_hash,
                "status": run.status,
                "started_at": run.started_at.isoformat(),
                "completed_at": (
                    run.completed_at.isoformat() if run.completed_at else None
                ),
                "latency_ms": run.latency_ms,
                "attempts": run.attempts,
                "finish_reason": run.finish_reason,
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "total_tokens": run.total_tokens,
                "estimated_cost_usd": run.estimated_cost_usd,
                "fallback_chain": run.fallback_chain,
                "error_code": run.error_code,
            }
            for run in ai_runs
        ],
        "ai_field_provenance": [
            {
                "run_id": record.run_id,
                "item_id": record.item_id,
                "analysis_version": record.analysis_version,
                "field_name": record.field_name,
                "source": record.source,
                "provider": record.provider,
                "model": record.model,
            }
            for record in field_provenance
        ],
        "enrichment_records": [
            {
                "id": record.id,
                "item_id": record.item_id,
                "ai_run_id": record.ai_run_id,
                "analysis_version": record.analysis_version,
                "schema_version": record.schema_version,
                "taxonomy_version": record.taxonomy_version,
                "summary": record.summary,
                "detailed_summary": record.detailed_summary,
                "topics": record.topics,
                "suggested_tags": record.suggested_tags,
                "classification": record.classification,
                "entities": record.entities,
                "key_phrases": record.key_phrases,
                "content_language": record.content_language,
                "confidence": record.confidence,
                "warnings": record.warnings,
                "provider": record.provider,
                "model": record.model,
                "prompt_version": record.prompt_version,
                "content_hash": record.content_hash,
                "field_provenance": record.field_provenance,
                "generated_at": record.generated_at.isoformat(),
            }
            for record in enrichments
        ],
        "ai_suggestion_feedback": [
            {
                "id": record.id,
                "client_id": record.client_id,
                "item_id": record.item_id,
                "enrichment_id": record.enrichment_id,
                "analysis_version": record.analysis_version,
                "suggestion_type": record.suggestion_type,
                "value": record.value,
                "action": record.action,
                "changed_item": record.changed_item,
                "item_revision_after": record.item_revision_after,
                "created_at": record.created_at.isoformat(),
            }
            for record in suggestion_feedback
        ],
        "ai_suggestion_preferences": [
            {
                "suggestion_type": record.suggestion_type,
                "normalized_value": record.normalized_value,
                "created_at": record.created_at.isoformat(),
            }
            for record in suggestion_preferences
        ],
        "item_embeddings": [
            {
                "item_id": embedding.item_id,
                "analysis_version": embedding.analysis_version,
                "chunk_id": embedding.chunk_id,
                "index_id": embedding.index_id,
                "provider": embedding.provider,
                "model": embedding.model,
                "dimensions": embedding.dimensions,
                "normalization": embedding.normalization,
                "index_version": embedding.index_version,
                "vector": embedding.vector,
                "content_hash": embedding.content_hash,
            }
            for embedding in embeddings
        ],
        "document_chunks": [
            {
                "item_id": chunk.item_id,
                "analysis_version": chunk.analysis_version,
                "chunk_id": chunk.chunk_key,
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "content_hash": chunk.content_hash,
            }
            for chunk in chunks
        ],
    }

    archive = io.BytesIO()
    try:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            output.writestr("memoryhive-export.json", json.dumps(manifest, indent=2))
            for item in items:
                for asset in item.assets:
                    extension = os.path.splitext(asset.original_filename or "")[1]
                    output.writestr(
                        f"assets/{asset.id}{extension}",
                        storage.get_file_bytes(asset.object_key),
                    )
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Unable to read stored assets"
        ) from exc
    archive.seek(0)
    filename = f"memoryhive-export-{datetime.now(timezone.utc).date().isoformat()}.zip"
    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("", status_code=204, responses=ERRORS)
async def delete_account(
    data: AccountDeleteRequest,
    current_user: CurrentUser,
    db: DbSession,
    storage: Storage,
) -> Response:
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Password is incorrect")
    await delete_user_account(
        db=db, storage=storage, user=current_user, event="account_deleted"
    )
    return Response(status_code=204)
