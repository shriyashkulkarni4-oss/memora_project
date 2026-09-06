"""Administrative dashboards and user-access management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.config import get_settings
from app.core.deps import CurrentAdmin, DbSession
from app.models import (
    AnalysisStatus,
    Asset,
    Item,
    ItemType,
    ProcessingJob,
    ProcessingStatus,
    User,
    UserRole,
)
from app.schemas.admin import (
    AdminBackupRecord,
    AdminBackupRunResponse,
    AdminBackupStatusResponse,
    AdminDashboardResponse,
    AdminProcessingJobResponse,
    AdminProcessingJobsPage,
    AdminProcessingJobStatus,
    AdminUserResponse,
    AdminUsersPage,
    AdminUserUpdate,
)
from app.schemas.common import ErrorResponse
from app.services.account_lifecycle import delete_user_account
from app.services.backup import (
    BackupCommandError,
    BackupCommandTimeoutError,
    BackupNotConfiguredError,
    BackupRecord,
    backup_status,
    run_backup,
)
from app.services.processing_worker import retry_failed_item
from app.services.storage import StorageService, get_storage_service

router = APIRouter()
Storage = Annotated[StorageService, Depends(get_storage_service)]

ERRORS = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


async def _count(db: DbSession, model: type[object], *conditions: object) -> int:
    value = await db.scalar(select(func.count()).select_from(model).where(*conditions))
    return value or 0


def _admin_user_response(
    user: User,
    *,
    item_count: int = 0,
    asset_count: int = 0,
    storage_bytes: int = 0,
) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        item_count=item_count,
        asset_count=asset_count,
        storage_bytes=storage_bytes,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _backup_record_response(record: BackupRecord) -> AdminBackupRecord:
    return AdminBackupRecord(
        path=record.path,
        created_at=record.created_at,
        size_bytes=record.size_bytes,
        has_postgres_dump=record.has_postgres_dump,
        has_minio_dir=record.has_minio_dir,
        has_checksums=record.has_checksums,
    )


def _item_display_title(item: Item) -> str | None:
    if item.title:
        return item.title
    if item.url:
        return item.url
    if item.raw_text:
        return item.raw_text[:80]
    return None


def _processing_job_response(
    job: ProcessingJob, item: Item, user: User
) -> AdminProcessingJobResponse:
    return AdminProcessingJobResponse(
        id=job.id,
        item_id=item.id,
        item_title=_item_display_title(item),
        item_type=ItemType(item.type),
        item_processing_status=ProcessingStatus(item.processing_status),
        user_id=user.id,
        user_email=user.email,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        next_attempt_at=job.next_attempt_at,
        locked_at=job.locked_at,
        last_error=job.last_error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


async def _load_processing_job_context(
    db: DbSession, job_id: str
) -> tuple[ProcessingJob, Item, User] | None:
    row = (
        await db.execute(
            select(ProcessingJob, Item, User)
            .join(Item, ProcessingJob.item_id == Item.id)
            .join(User, Item.user_id == User.id)
            .where(ProcessingJob.id == job_id)
        )
    ).one_or_none()
    if row is None:
        return None
    job, item, user = row
    return job, item, user


@router.get("/dashboard", response_model=AdminDashboardResponse, responses=ERRORS)
async def get_admin_dashboard(
    _admin: CurrentAdmin, db: DbSession
) -> AdminDashboardResponse:
    storage_bytes = await db.scalar(
        select(func.coalesce(func.sum(Asset.size_bytes), 0))
    )
    return AdminDashboardResponse(
        users_total=await _count(db, User),
        active_users=await _count(db, User, User.is_active.is_(True)),
        disabled_users=await _count(db, User, User.is_active.is_(False)),
        admin_users=await _count(db, User, User.role == UserRole.ADMIN.value),
        items_total=await _count(db, Item, Item.deleted_at.is_(None)),
        archived_items=await _count(
            db, Item, Item.deleted_at.is_(None), Item.is_archived.is_(True)
        ),
        assets_total=await _count(db, Asset),
        storage_bytes=int(storage_bytes or 0),
        processing_pending=await _count(
            db,
            ProcessingJob,
            ProcessingJob.status.in_(["pending", "processing"]),
        ),
        processing_failed=await _count(
            db,
            ProcessingJob,
            ProcessingJob.status == ProcessingStatus.FAILED.value,
        ),
        analysis_pending=await _count(
            db,
            Item,
            Item.deleted_at.is_(None),
            Item.analysis_status.in_(
                [AnalysisStatus.PENDING.value, AnalysisStatus.ANALYZING.value]
            ),
        ),
        analysis_failed=await _count(
            db,
            Item,
            Item.deleted_at.is_(None),
            Item.analysis_status == AnalysisStatus.FAILED.value,
        ),
    )


@router.get("/users", response_model=AdminUsersPage, responses=ERRORS)
async def list_admin_users(
    _admin: CurrentAdmin,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminUsersPage:
    item_counts = (
        select(Item.user_id, func.count(Item.id).label("item_count"))
        .where(Item.deleted_at.is_(None))
        .group_by(Item.user_id)
        .subquery()
    )
    asset_counts = (
        select(
            Asset.user_id,
            func.count(Asset.id).label("asset_count"),
            func.coalesce(func.sum(Asset.size_bytes), 0).label("storage_bytes"),
        )
        .group_by(Asset.user_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                User,
                func.coalesce(item_counts.c.item_count, 0),
                func.coalesce(asset_counts.c.asset_count, 0),
                func.coalesce(asset_counts.c.storage_bytes, 0),
            )
            .outerjoin(item_counts, item_counts.c.user_id == User.id)
            .outerjoin(asset_counts, asset_counts.c.user_id == User.id)
            .order_by(User.created_at.desc(), User.email.asc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    users = [
        _admin_user_response(
            user,
            item_count=int(item_count),
            asset_count=int(asset_count),
            storage_bytes=int(storage_bytes),
        )
        for user, item_count, asset_count, storage_bytes in rows
    ]
    return AdminUsersPage(
        users=users,
        total=await _count(db, User),
        limit=limit,
        offset=offset,
    )


@router.get("/backup", response_model=AdminBackupStatusResponse, responses=ERRORS)
async def get_admin_backup_status(_admin: CurrentAdmin) -> AdminBackupStatusResponse:
    status_snapshot = backup_status(get_settings())
    recent = [_backup_record_response(record) for record in status_snapshot.recent]
    return AdminBackupStatusResponse(
        configured=status_snapshot.configured,
        command=status_snapshot.command,
        backup_root=status_snapshot.backup_root,
        retention_days=status_snapshot.retention_days,
        latest=recent[0] if recent else None,
        recent=recent,
    )


@router.post(
    "/backup/run",
    response_model=AdminBackupRunResponse,
    responses={**ERRORS, 503: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
)
async def run_admin_backup(_admin: CurrentAdmin) -> AdminBackupRunResponse:
    try:
        result = await run_backup(get_settings())
    except BackupNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BackupCommandTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except BackupCommandError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return AdminBackupRunResponse(
        status="succeeded",
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        latest=_backup_record_response(result.latest) if result.latest else None,
        duration_seconds=result.duration_seconds,
    )


@router.get(
    "/processing/jobs",
    response_model=AdminProcessingJobsPage,
    responses=ERRORS,
)
async def list_admin_processing_jobs(
    _admin: CurrentAdmin,
    db: DbSession,
    job_status: Annotated[
        AdminProcessingJobStatus | None, Query(alias="status")
    ] = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminProcessingJobsPage:
    conditions = []
    if job_status:
        conditions.append(ProcessingJob.status == job_status)

    query = (
        select(ProcessingJob, Item, User)
        .join(Item, ProcessingJob.item_id == Item.id)
        .join(User, Item.user_id == User.id)
        .order_by(ProcessingJob.updated_at.desc(), ProcessingJob.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if conditions:
        query = query.where(*conditions)

    rows = (await db.execute(query)).all()
    return AdminProcessingJobsPage(
        jobs=[_processing_job_response(job, item, user) for job, item, user in rows],
        total=await _count(db, ProcessingJob, *conditions),
        limit=limit,
        offset=offset,
    )


@router.post(
    "/processing/jobs/{job_id}/retry",
    response_model=AdminProcessingJobResponse,
    responses={**ERRORS, 409: {"model": ErrorResponse}},
)
async def retry_admin_processing_job(
    job_id: str,
    _admin: CurrentAdmin,
    db: DbSession,
) -> AdminProcessingJobResponse:
    row = await _load_processing_job_context(db, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Processing job not found")
    job, item, _user = row
    if job.status != "failed":
        raise HTTPException(
            status_code=409, detail="Only failed processing jobs can be retried"
        )
    if item.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Deleted items cannot be retried")
    if ItemType(item.type) == ItemType.TEXT:
        raise HTTPException(status_code=400, detail="Text items do not need processing")

    try:
        next_job = await retry_failed_item(db, item)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.flush()
    next_job_id = next_job.id
    await db.commit()

    next_row = await _load_processing_job_context(db, next_job_id)
    if next_row is None:
        raise HTTPException(status_code=404, detail="Retried job was not found")
    return _processing_job_response(*next_row)


@router.patch("/users/{user_id}", response_model=AdminUserResponse, responses=ERRORS)
async def update_admin_user(
    user_id: str,
    data: AdminUserUpdate,
    admin: CurrentAdmin,
    db: DbSession,
) -> AdminUserResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and data.is_active is False:
        raise HTTPException(status_code=400, detail="Admins cannot disable themselves")
    if user.id == admin.id and data.role == UserRole.USER:
        raise HTTPException(status_code=400, detail="Admins cannot demote themselves")

    changes = data.model_dump(exclude_unset=True)
    if "role" in changes and changes["role"] is not None:
        user.role = changes["role"].value
    if "is_active" in changes and changes["is_active"] is not None:
        user.is_active = changes["is_active"]
    await db.commit()
    await db.refresh(user)
    return _admin_user_response(user)


@router.delete(
    "/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS
)
async def delete_admin_user(
    user_id: str,
    admin: CurrentAdmin,
    db: DbSession,
    storage: Storage,
) -> Response:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot delete themselves")
    await delete_user_account(
        db=db, storage=storage, user=user, event="admin_user_deleted"
    )
    return Response(status_code=204)
