"""Canonical Item capture and retrieval endpoints."""

import asyncio
import base64
import hashlib
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Annotated
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from PIL import Image, UnidentifiedImageError
from sqlalchemy import and_, delete, func, literal, or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload
from temporalio.client import Client

from app.ai.budgets import DatabaseBudgetGuard
from app.ai.embedding_pipeline import EmbeddingPipeline
from app.ai.factory import build_ai_gateway
from app.ai.gateway import ProviderError
from app.ai.hybrid_search import lexical_signals, reciprocal_rank_fusion
from app.ai.retrieval_eval import cosine_similarity
from app.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.models import (
    AnalysisStatus,
    Asset,
    Category,
    DocumentChunk,
    EnrichmentRecord,
    Item,
    ItemEmbedding,
    ItemType,
    ProcessingJob,
    ProcessingStatus,
    Tag,
)
from app.schemas.common import ErrorResponse
from app.schemas.item import (
    EnrichmentRecordResponse,
    ItemChangesResponse,
    ItemCreate,
    ItemListResponse,
    ItemResponse,
    ItemStats,
    ItemUpdate,
    ProcessingStateResponse,
    SearchMatchResponse,
)
from app.services.analysis_dispatch import request_item_analysis, retry_item_analysis
from app.services.storage import StorageService, get_storage_service
from app.services.urls import normalize_url
from app.temporal_pipeline.workflows import AnalyzeItemWorkflow

router = APIRouter()
settings = get_settings()
Storage = Annotated[StorageService, Depends(get_storage_service)]

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid request"},
    401: {"model": ErrorResponse, "description": "Authentication required"},
    404: {"model": ErrorResponse, "description": "Item not found"},
    409: {"model": ErrorResponse, "description": "Revision or identifier conflict"},
    422: {"model": ErrorResponse, "description": "Validation failed"},
}


def _encode_cursor(item: Item) -> str:
    value = f"{item.created_at.isoformat()}|{item.id}"
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = base64.urlsafe_b64decode(padded.encode()).decode()
        created_at, item_id = value.rsplit("|", 1)
        return datetime.fromisoformat(created_at), item_id
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


def _encode_change_cursor(item: Item) -> str:
    value = f"{item.updated_at.isoformat()}|{item.id}"
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _detected_image_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def _inspect_image(content: bytes) -> tuple[str, int, int]:
    detected_type = _detected_image_type(content)
    if detected_type is None:
        raise HTTPException(status_code=415, detail="Unsupported screenshot format")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
            image_format = image.format
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=415, detail="Screenshot image is invalid"
        ) from exc
    format_types = {
        "PNG": "image/png",
        "JPEG": "image/jpeg",
        "GIF": "image/gif",
        "WEBP": "image/webp",
    }
    if format_types.get(image_format) != detected_type:
        raise HTTPException(
            status_code=415, detail="Screenshot image format is invalid"
        )
    return detected_type, width, height


def _response(
    item: Item, search_match: SearchMatchResponse | None = None
) -> ItemResponse:
    return ItemResponse(
        id=item.id,
        user_id=item.user_id,
        type=item.type,
        url=item.url,
        raw_text=item.raw_text,
        title=item.title,
        description=item.description,
        notes=item.notes,
        source=item.source,
        source_domain=item.source_domain,
        author=item.author,
        published_at=item.published_at,
        favicon_url=item.favicon_url,
        extracted_text=item.extracted_text,
        language=item.language,
        summary=item.summary,
        metadata=item.item_metadata,
        processing_status=item.processing_status,
        processing_error=item.processing_error,
        analysis_status=item.analysis_status,
        analysis_error=item.analysis_error,
        analysis_version=item.analysis_version,
        analysis_requested_at=item.analysis_requested_at,
        analysis_started_at=item.analysis_started_at,
        analysis_completed_at=item.analysis_completed_at,
        category_id=item.category_id,
        tags=item.tags,
        assets=item.assets,
        is_favorite=item.is_favorite,
        is_archived=item.is_archived,
        read_count=item.read_count,
        last_visited_at=item.last_visited_at,
        revision=item.revision,
        deleted_at=item.deleted_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        search_match=search_match,
    )


def _text_match_condition(value: str):
    pattern = f"%{value}%"
    searchable = [
        Item.title,
        Item.url,
        Item.raw_text,
        Item.extracted_text,
        Item.summary,
        Item.description,
        Item.notes,
        Item.source_domain,
    ]
    text_matches = [column.ilike(pattern) for column in searchable]
    return searchable, text_matches, pattern


async def _rank_search(
    db: DbSession,
    base_query,
    *,
    user_id: str,
    value: str,
    limit: int,
) -> tuple[list[Item], dict[str, SearchMatchResponse], bool]:
    current_settings = get_settings()
    candidate_limit = max(limit + 1, current_settings.ai_search_candidate_limit)
    searchable, text_matches, pattern = _text_match_condition(value)
    if db.bind and db.bind.dialect.name == "postgresql":
        document_text = func.coalesce(searchable[0], "")
        for column in searchable[1:]:
            document_text = document_text + literal(" ") + func.coalesce(column, "")
        document = func.to_tsvector("simple", document_text)
        text_matches.append(
            document.op("@@")(func.websearch_to_tsquery("simple", value))
        )
    keyword_condition = or_(
        *text_matches,
        Item.tags.any(and_(Tag.user_id == user_id, Tag.name.ilike(pattern))),
    )
    keyword_result = await db.execute(
        base_query.where(keyword_condition)
        .order_by(Item.created_at.desc(), Item.id.desc())
        .limit(candidate_limit)
    )
    keyword_items = list(keyword_result.scalars().unique())
    lexical = [lexical_signals(item, value) for item in keyword_items]
    semantic: list[tuple[str, float, str | None]] = []
    eligible_by_id = {item.id: item for item in keyword_items}

    if (
        current_settings.ai_hybrid_search_enabled
        and current_settings.ai_embeddings_route
    ):
        eligible_result = await db.execute(
            base_query.order_by(Item.created_at.desc(), Item.id.desc()).limit(
                candidate_limit
            )
        )
        eligible_items = list(eligible_result.scalars().unique())
        eligible_by_id.update({item.id: item for item in eligible_items})
        try:
            started = time.perf_counter()
            async with asyncio.timeout(
                current_settings.ai_search_latency_budget_ms / 1_000
            ):
                if db.bind is None:
                    raise ValueError("database binding is unavailable")
                session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
                query_embedding = await EmbeddingPipeline(
                    session_factory,
                    build_ai_gateway(current_settings),
                    current_settings,
                    DatabaseBudgetGuard(session_factory, current_settings),
                ).embed_query(value, user_id=user_id)
            if (
                time.perf_counter() - started
            ) * 1_000 <= current_settings.ai_search_latency_budget_ms:
                vectors = list(
                    await db.scalars(
                        select(ItemEmbedding).where(
                            ItemEmbedding.user_id == user_id,
                            ItemEmbedding.index_id == query_embedding.index_id,
                            ItemEmbedding.item_id.in_(eligible_by_id),
                        )
                    )
                )
                chunk_keys = {vector.chunk_id for vector in vectors}
                chunks = (
                    list(
                        await db.scalars(
                            select(DocumentChunk).where(
                                DocumentChunk.user_id == user_id,
                                DocumentChunk.chunk_key.in_(chunk_keys),
                            )
                        )
                    )
                    if chunk_keys
                    else []
                )
                chunk_text = {
                    (chunk.item_id, chunk.analysis_version, chunk.chunk_key): chunk.text
                    for chunk in chunks
                }
                best: dict[str, tuple[float, str | None]] = {}
                for vector in vectors:
                    item = eligible_by_id.get(vector.item_id)
                    if item is None or vector.analysis_version != item.analysis_version:
                        continue
                    similarity = cosine_similarity(
                        query_embedding.vector, vector.vector
                    )
                    if similarity < current_settings.ai_search_semantic_threshold:
                        continue
                    snippet = chunk_text.get(
                        (vector.item_id, vector.analysis_version, vector.chunk_id)
                    )
                    if (
                        vector.item_id not in best
                        or similarity > best[vector.item_id][0]
                    ):
                        best[vector.item_id] = (similarity, snippet)
                semantic = [
                    (item_id, score, snippet)
                    for item_id, (score, snippet) in best.items()
                ]
        except (ProviderError, TimeoutError, ValueError):
            semantic = []

    ranked = reciprocal_rank_fusion(
        lexical,
        semantic,
        rrf_k=current_settings.ai_search_rrf_k,
        keyword_weight=current_settings.ai_search_keyword_weight,
        semantic_weight=current_settings.ai_search_semantic_weight,
    )
    selected = ranked[: limit + 1]
    has_more = len(selected) > limit
    selected = selected[:limit]
    matches = {
        match.item_id: SearchMatchResponse(
            score=match.score,
            reasons=list(match.reasons),
            snippet=match.snippet,
            semantic_score=match.semantic_score,
        )
        for match in selected
    }
    return (
        [eligible_by_id[match.item_id] for match in selected],
        matches,
        has_more,
    )


async def _load_item(db: DbSession, user_id: str, item_id: str) -> Item:
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.tags), selectinload(Item.assets))
        .where(Item.id == item_id, Item.user_id == user_id, Item.deleted_at.is_(None))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


async def _resolve_category(
    db: DbSession, user_id: str, category_id: str | None
) -> str | None:
    if category_id is None:
        return None
    category = await db.scalar(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    if category is None:
        raise HTTPException(status_code=400, detail="Category does not belong to user")
    return category.id


async def _resolve_tags(db: DbSession, user_id: str, names: list[str]) -> list[Tag]:
    tags: list[Tag] = []
    normalized_names = {
        " ".join(name.lower().split()) for name in names if name.strip()
    }
    for name in sorted(normalized_names):
        if len(name) > 50:
            raise HTTPException(status_code=422, detail="Tag name is too long")
        tag = await db.scalar(
            select(Tag).where(Tag.user_id == user_id, Tag.name == name)
        )
        if tag is None:
            tag = Tag(id=str(uuid.uuid4()), user_id=user_id, name=name)
            db.add(tag)
        tags.append(tag)
    return tags


@router.get("", response_model=ItemListResponse, responses=ERROR_RESPONSES)
async def list_items(
    current_user: CurrentUser,
    db: DbSession,
    cursor: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    item_type: ItemType | None = Query(default=None, alias="type"),
    source: str | None = None,
    category_id: str | None = None,
    is_favorite: bool | None = None,
    is_archived: bool = False,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    processing_status: ProcessingStatus | None = None,
    tag: list[str] | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=200),
) -> ItemListResponse:
    query = (
        select(Item)
        .options(selectinload(Item.tags), selectinload(Item.assets))
        .where(
            Item.user_id == current_user.id,
            Item.deleted_at.is_(None),
            Item.is_archived.is_(is_archived),
        )
    )
    if cursor:
        cursor_time, cursor_id = _decode_cursor(cursor)
        query = query.where(
            or_(
                Item.created_at < cursor_time,
                and_(Item.created_at == cursor_time, Item.id < cursor_id),
            )
        )
    if item_type:
        query = query.where(Item.type == item_type)
    if source:
        query = query.where(Item.source == source)
    if category_id:
        query = query.where(Item.category_id == category_id)
    if is_favorite is not None:
        query = query.where(Item.is_favorite.is_(is_favorite))
    if created_from:
        query = query.where(Item.created_at >= created_from)
    if created_to:
        query = query.where(Item.created_at <= created_to)
    if processing_status:
        query = query.where(Item.processing_status == processing_status)
    for tag_name in tag or []:
        normalized_tag = " ".join(tag_name.lower().split())
        query = query.where(
            Item.tags.any(
                and_(Tag.user_id == current_user.id, Tag.name == normalized_tag)
            )
        )
    if q:
        value = q.strip()
        items, search_matches, has_more = await _rank_search(
            db,
            query,
            user_id=current_user.id,
            value=value,
            limit=limit,
        )
        return ItemListResponse(
            items=[_response(item, search_matches[item.id]) for item in items],
            next_cursor=_encode_cursor(items[-1]) if has_more and items else None,
            has_more=has_more,
            limit=limit,
        )

    result = await db.execute(
        query.order_by(Item.created_at.desc(), Item.id.desc()).limit(limit + 1)
    )
    records = list(result.scalars().unique())
    has_more = len(records) > limit
    items = records[:limit]
    return ItemListResponse(
        items=[_response(item) for item in items],
        next_cursor=_encode_cursor(items[-1]) if has_more else None,
        has_more=has_more,
        limit=limit,
    )


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def create_item(
    data: ItemCreate, current_user: CurrentUser, db: DbSession
) -> ItemResponse:
    item_id = str(data.id or uuid.uuid4())
    if await db.scalar(select(Item.id).where(Item.id == item_id)):
        raise HTTPException(status_code=409, detail="Item identifier already exists")

    category_id = await _resolve_category(
        db, current_user.id, str(data.category_id) if data.category_id else None
    )
    url = str(data.url) if data.url else None
    normalized_url = normalize_url(url) if url else None
    if normalized_url and await db.scalar(
        select(Item.id).where(
            Item.user_id == current_user.id,
            Item.normalized_url == normalized_url,
            Item.deleted_at.is_(None),
        )
    ):
        raise HTTPException(status_code=409, detail="This link is already saved")
    created_at = data.created_at or datetime.now(timezone.utc)
    item = Item(
        id=item_id,
        user_id=current_user.id,
        type=data.type,
        url=url,
        normalized_url=normalized_url,
        raw_text=data.raw_text,
        title=data.title,
        description=data.description,
        notes=data.notes,
        source=data.source,
        source_domain=urlparse(url).hostname if url else None,
        category_id=category_id,
        item_metadata=data.metadata,
        analysis_status=AnalysisStatus.PENDING,
        analysis_requested_at=created_at,
        processing_status=(
            ProcessingStatus.READY
            if data.type == ItemType.TEXT
            else ProcessingStatus.PENDING
        ),
        created_at=created_at,
        updated_at=created_at,
    )
    item.tags = await _resolve_tags(db, current_user.id, data.tags)
    db.add(item)
    await request_item_analysis(
        db, item, reason="capture", settings=settings, requested_at=created_at
    )
    await db.commit()
    return _response(await _load_item(db, current_user.id, item.id))


@router.get("/stats", response_model=ItemStats, responses=ERROR_RESPONSES)
async def get_item_stats(current_user: CurrentUser, db: DbSession) -> ItemStats:
    owned = [Item.user_id == current_user.id, Item.deleted_at.is_(None)]

    async def count(*conditions: object) -> int:
        value = await db.scalar(
            select(func.count()).select_from(Item).where(*owned, *conditions)
        )
        return value or 0

    by_type = {item_type: await count(Item.type == item_type) for item_type in ItemType}
    return ItemStats(
        total_items=await count(),
        active_items=await count(Item.is_archived.is_(False)),
        favorite_items=await count(Item.is_favorite.is_(True)),
        archived_items=await count(Item.is_archived.is_(True)),
        pending_processing=await count(
            Item.processing_status.in_(
                [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]
            )
        ),
        failed_processing=await count(
            Item.processing_status == ProcessingStatus.FAILED
        ),
        pending_analysis=await count(
            Item.analysis_status.in_(
                [
                    AnalysisStatus.PENDING,
                    AnalysisStatus.SCHEDULED,
                    AnalysisStatus.ANALYZING,
                ]
            )
        ),
        failed_analysis=await count(Item.analysis_status == AnalysisStatus.FAILED),
        by_type=by_type,
    )


@router.get("/changes", response_model=ItemChangesResponse, responses=ERROR_RESPONSES)
async def list_item_changes(
    current_user: CurrentUser,
    db: DbSession,
    since: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> ItemChangesResponse:
    """Return active records and tombstones in stable update order."""
    server_time = datetime.now(timezone.utc)
    query = (
        select(Item)
        .options(selectinload(Item.tags), selectinload(Item.assets))
        .where(Item.user_id == current_user.id, Item.updated_at <= server_time)
    )
    if cursor:
        cursor_time, cursor_id = _decode_cursor(cursor)
        query = query.where(
            or_(
                Item.updated_at > cursor_time,
                and_(Item.updated_at == cursor_time, Item.id > cursor_id),
            )
        )
    elif since:
        query = query.where(Item.updated_at > since)
    result = await db.execute(
        query.order_by(Item.updated_at.asc(), Item.id.asc()).limit(limit + 1)
    )
    records = list(result.scalars().unique())
    has_more = len(records) > limit
    items = records[:limit]
    return ItemChangesResponse(
        items=[_response(item) for item in items],
        next_cursor=_encode_change_cursor(items[-1]) if has_more else None,
        has_more=has_more,
        server_time=server_time,
    )


@router.post(
    "/screenshot",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def create_screenshot_item(
    current_user: CurrentUser,
    db: DbSession,
    storage: Storage,
    file: UploadFile = File(...),
    id: str | None = Form(default=None),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    source: str | None = Form(default="screenshot"),
    category_id: str | None = Form(default=None),
    tags: str | None = Form(default=None),
) -> ItemResponse:
    try:
        item_id = str(uuid.UUID(id)) if id else str(uuid.uuid4())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid item UUID") from exc
    if await db.scalar(select(Item.id).where(Item.id == item_id)):
        raise HTTPException(status_code=409, detail="Item identifier already exists")

    max_size = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read(max_size + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Screenshot file is empty")
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="Screenshot exceeds upload limit")
    detected_type, width, height = _inspect_image(content)
    if file.content_type and file.content_type not in {
        detected_type,
        "image/jpg" if detected_type == "image/jpeg" else detected_type,
    }:
        raise HTTPException(
            status_code=415, detail="Screenshot content type does not match file"
        )

    owned_category = await _resolve_category(db, current_user.id, category_id)
    tag_names = [
        part.strip().lower() for part in (tags or "").split(",") if part.strip()
    ]
    uploaded = storage.upload_bytes(
        content,
        content_type=detected_type,
        original_filename=file.filename,
        user_id=current_user.id,
    )
    now = datetime.now(timezone.utc)
    item = Item(
        id=item_id,
        user_id=current_user.id,
        type=ItemType.SCREENSHOT,
        title=title.strip() if title and title.strip() else None,
        description=description,
        notes=notes,
        source=source,
        category_id=owned_category,
        processing_status=ProcessingStatus.PENDING,
        analysis_status=AnalysisStatus.PENDING,
        analysis_requested_at=now,
        created_at=now,
        updated_at=now,
    )
    item.tags = await _resolve_tags(db, current_user.id, tag_names)
    item.assets.append(
        Asset(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            object_key=uploaded["file_key"],
            original_filename=file.filename,
            mime_type=detected_type,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            width=width,
            height=height,
        )
    )
    db.add(item)
    await request_item_analysis(
        db, item, reason="capture", settings=settings, requested_at=now
    )
    try:
        await db.commit()
    except Exception:
        storage.delete_file(uploaded["file_key"])
        raise
    return _response(await _load_item(db, current_user.id, item.id))


@router.get("/{item_id}", response_model=ItemResponse, responses=ERROR_RESPONSES)
async def get_item(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> ItemResponse:
    return _response(await _load_item(db, current_user.id, item_id))


@router.get(
    "/{item_id}/enrichments",
    response_model=list[EnrichmentRecordResponse],
    responses=ERROR_RESPONSES,
)
async def list_item_enrichments(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> list[EnrichmentRecordResponse]:
    item = await _load_item(db, current_user.id, item_id)
    records = list(
        await db.scalars(
            select(EnrichmentRecord)
            .where(EnrichmentRecord.item_id == item.id)
            .order_by(EnrichmentRecord.analysis_version.desc())
        )
    )
    return [
        EnrichmentRecordResponse.model_validate(record, from_attributes=True)
        for record in records
    ]


@router.get(
    "/{item_id}/processing",
    response_model=ProcessingStateResponse,
    responses=ERROR_RESPONSES,
)
async def get_processing_state(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> ProcessingStateResponse:
    item = await _load_item(db, current_user.id, item_id)
    return ProcessingStateResponse(
        item_id=item.id,
        status=item.processing_status,
        error=item.processing_error,
        updated_at=item.updated_at,
    )


@router.post(
    "/{item_id}/processing/retry",
    response_model=ProcessingStateResponse,
    responses=ERROR_RESPONSES,
)
async def retry_item_processing(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> ProcessingStateResponse:
    item = await _load_item(db, current_user.id, item_id)
    try:
        await retry_item_analysis(db, item, settings=settings)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    return ProcessingStateResponse(
        item_id=item.id,
        status=item.processing_status,
        error=item.processing_error,
        updated_at=item.updated_at,
    )


@router.post(
    "/{item_id}/analysis/cancel",
    response_model=ProcessingStateResponse,
    responses=ERROR_RESPONSES,
)
async def cancel_item_analysis(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> ProcessingStateResponse:
    item = await _load_item(db, current_user.id, item_id)
    job = await db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.item_id == item.id,
            ProcessingJob.analysis_version == item.analysis_version,
            ProcessingJob.execution_backend == "temporal",
            ProcessingJob.status.in_(("pending", "scheduled", "processing")),
        )
    )
    if job is None or not job.temporal_workflow_id:
        raise HTTPException(
            status_code=409, detail="Item has no running Temporal analysis"
        )
    client = await Client.connect(
        settings.temporal_address, namespace=settings.temporal_namespace
    )
    handle = client.get_workflow_handle(job.temporal_workflow_id)
    await handle.signal(AnalyzeItemWorkflow.request_cancel)
    job.cancel_requested = True
    await db.commit()
    return ProcessingStateResponse(
        item_id=item.id,
        status=item.processing_status,
        error="Analysis cancellation requested",
        updated_at=item.updated_at,
    )


@router.patch("/{item_id}", response_model=ItemResponse, responses=ERROR_RESPONSES)
async def update_item(
    item_id: str, data: ItemUpdate, current_user: CurrentUser, db: DbSession
) -> ItemResponse:
    item = await _load_item(db, current_user.id, item_id)
    if data.expected_revision and data.expected_revision != item.revision:
        raise HTTPException(status_code=409, detail="Item revision conflict")

    update = data.model_dump(exclude_unset=True)
    update.pop("expected_revision", None)
    tag_names = update.pop("tags", None)
    if "category_id" in update:
        category = update.pop("category_id")
        item.category_id = await _resolve_category(
            db, current_user.id, str(category) if category else None
        )
    if "url" in update:
        update["url"] = str(update["url"]) if update["url"] else None
        item.source_domain = urlparse(update["url"]).hostname if update["url"] else None
        normalized_url = normalize_url(update["url"]) if update["url"] else None
        if normalized_url and await db.scalar(
            select(Item.id).where(
                Item.user_id == current_user.id,
                Item.normalized_url == normalized_url,
                Item.deleted_at.is_(None),
                Item.id != item.id,
            )
        ):
            raise HTTPException(status_code=409, detail="This link is already saved")
        item.normalized_url = normalized_url
    content_fields = {"url", "raw_text", "title", "description", "notes"}
    analysis_content_changed = any(field in update for field in content_fields)
    for key, value in update.items():
        setattr(item, key, value)
    if item.type == ItemType.LINK and not item.url:
        raise HTTPException(status_code=400, detail="Link items require a URL")
    if item.type == ItemType.TEXT and not item.raw_text:
        raise HTTPException(status_code=400, detail="Text items require raw text")
    if tag_names is not None:
        item.tags = await _resolve_tags(db, current_user.id, tag_names)
        # An explicit tag save is a manual override; future suggestion undo must
        # never remove a tag the user has since affirmed manually.
        item.item_metadata = {
            **(item.item_metadata or {}),
            "ai_applied_tags": {},
        }
    if analysis_content_changed:
        await request_item_analysis(
            db,
            item,
            reason="content_updated",
            settings=settings,
            increment_version=True,
        )
    item.revision += 1
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return _response(await _load_item(db, current_user.id, item.id))


async def _set_flag(
    item_id: str,
    field: str,
    value: bool,
    current_user: CurrentUser,
    db: DbSession,
) -> ItemResponse:
    item = await _load_item(db, current_user.id, item_id)
    setattr(item, field, value)
    item.revision += 1
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return _response(await _load_item(db, current_user.id, item.id))


@router.put(
    "/{item_id}/favorite", response_model=ItemResponse, responses=ERROR_RESPONSES
)
async def favorite_item(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> ItemResponse:
    return await _set_flag(item_id, "is_favorite", True, current_user, db)


@router.delete(
    "/{item_id}/favorite", response_model=ItemResponse, responses=ERROR_RESPONSES
)
async def unfavorite_item(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> ItemResponse:
    return await _set_flag(item_id, "is_favorite", False, current_user, db)


@router.put(
    "/{item_id}/archive", response_model=ItemResponse, responses=ERROR_RESPONSES
)
async def archive_item(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> ItemResponse:
    return await _set_flag(item_id, "is_archived", True, current_user, db)


@router.delete(
    "/{item_id}/archive", response_model=ItemResponse, responses=ERROR_RESPONSES
)
async def restore_item(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> ItemResponse:
    return await _set_flag(item_id, "is_archived", False, current_user, db)


@router.delete("/{item_id}", status_code=204, responses=ERROR_RESPONSES)
async def delete_item(item_id: str, current_user: CurrentUser, db: DbSession) -> None:
    item = await _load_item(db, current_user.id, item_id)
    await db.execute(delete(ItemEmbedding).where(ItemEmbedding.item_id == item.id))
    await db.execute(delete(DocumentChunk).where(DocumentChunk.item_id == item.id))
    item.deleted_at = datetime.now(timezone.utc)
    item.revision += 1
    item.updated_at = item.deleted_at
    await db.commit()
