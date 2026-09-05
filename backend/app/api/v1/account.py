"""Portable export and durable account deletion endpoints."""

import io
import json
import os
import uuid
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
from app.models import Asset, Category, Item, LifecycleAudit, StorageDeletionJob, Tag
from app.schemas.account import AccountDeleteRequest
from app.schemas.common import ErrorResponse
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
    object_keys = list(
        await db.scalars(
            select(Asset.object_key).where(Asset.user_id == current_user.id)
        )
    )
    audit = LifecycleAudit(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        event="account_deleted",
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
    await db.delete(current_user)
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
    return Response(status_code=204)
