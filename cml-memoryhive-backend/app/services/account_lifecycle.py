"""Account lifecycle operations shared by user and admin APIs."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AIFieldProvenance,
    AIRun,
    AISuggestionFeedback,
    AISuggestionPreference,
    AIUsageEvent,
    Asset,
    DocumentChunk,
    EnrichmentRecord,
    ItemEmbedding,
    ItemInteraction,
    LifecycleAudit,
    StorageDeletionJob,
    User,
)
from app.services.storage import StorageService


async def delete_user_account(
    *,
    db: AsyncSession,
    storage: StorageService,
    user: User,
    event: str,
) -> None:
    """Delete a user and queue/attempt storage cleanup with an audit trail."""
    object_keys = list(
        await db.scalars(select(Asset.object_key).where(Asset.user_id == user.id))
    )
    audit = LifecycleAudit(
        id=str(uuid.uuid4()),
        user_id=user.id,
        event=event,
        status="pending",
        object_count=len(object_keys),
    )
    db.add(audit)
    jobs = [
        StorageDeletionJob(
            id=str(uuid.uuid4()), audit_id=audit.id, object_key=object_key
        )
        for object_key in object_keys
    ]
    db.add_all(jobs)
    # Explicit deletion keeps behavior deterministic even where database FK
    # cascade enforcement differs (for example, SQLite test/export tooling).
    await db.execute(
        delete(AIFieldProvenance).where(AIFieldProvenance.user_id == user.id)
    )
    await db.execute(delete(ItemEmbedding).where(ItemEmbedding.user_id == user.id))
    await db.execute(delete(DocumentChunk).where(DocumentChunk.user_id == user.id))
    await db.execute(delete(ItemInteraction).where(ItemInteraction.user_id == user.id))
    await db.execute(
        delete(AISuggestionFeedback).where(AISuggestionFeedback.user_id == user.id)
    )
    await db.execute(
        delete(AISuggestionPreference).where(AISuggestionPreference.user_id == user.id)
    )
    await db.execute(
        delete(EnrichmentRecord).where(EnrichmentRecord.user_id == user.id)
    )
    await db.execute(delete(AIUsageEvent).where(AIUsageEvent.user_id == user.id))
    await db.execute(delete(AIRun).where(AIRun.user_id == user.id))
    await db.delete(user)
    await db.commit()

    failures = 0
    for job in jobs:
        try:
            removed = storage.delete_file(job.object_key)
        except Exception as exc:  # pragma: no cover - storage adapters vary
            removed = False
            job.last_error = str(exc)[:1000]
        job.attempts += 1
        if removed:
            await db.delete(job)
        else:
            failures += 1
            job.last_error = job.last_error or "Storage adapter rejected deletion"

    audit.error_count = failures
    audit.status = "completed" if failures == 0 else "retry_pending"
    audit.completed_at = datetime.now(timezone.utc) if failures == 0 else None
    await db.commit()
