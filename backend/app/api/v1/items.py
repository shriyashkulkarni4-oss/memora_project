"""Canonical Item capture and retrieval endpoints."""

import base64
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.models import Category, Item, ItemType, ProcessingStatus, Tag
from app.schemas.common import ErrorResponse
from app.schemas.item import ItemCreate, ItemListResponse, ItemResponse, ItemUpdate

router = APIRouter()

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


def _response(item: Item) -> ItemResponse:
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
    for name in names:
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
    created_at = data.created_at or datetime.now(timezone.utc)
    item = Item(
        id=item_id,
        user_id=current_user.id,
        type=data.type,
        url=url,
        raw_text=data.raw_text,
        title=data.title,
        description=data.description,
        notes=data.notes,
        source=data.source,
        source_domain=urlparse(url).hostname if url else None,
        category_id=category_id,
        item_metadata=data.metadata,
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
    await db.commit()
    return _response(await _load_item(db, current_user.id, item.id))


@router.get("/{item_id}", response_model=ItemResponse, responses=ERROR_RESPONSES)
async def get_item(
    item_id: str, current_user: CurrentUser, db: DbSession
) -> ItemResponse:
    return _response(await _load_item(db, current_user.id, item_id))


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
    for key, value in update.items():
        setattr(item, key, value)
    if item.type == ItemType.LINK and not item.url:
        raise HTTPException(status_code=400, detail="Link items require a URL")
    if item.type == ItemType.TEXT and not item.raw_text:
        raise HTTPException(status_code=400, detail="Text items require raw text")
    if tag_names is not None:
        item.tags = await _resolve_tags(db, current_user.id, tag_names)
    item.revision += 1
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return _response(await _load_item(db, current_user.id, item.id))


@router.delete("/{item_id}", status_code=204, responses=ERROR_RESPONSES)
async def delete_item(item_id: str, current_user: CurrentUser, db: DbSession) -> None:
    item = await _load_item(db, current_user.id, item_id)
    item.deleted_at = datetime.now(timezone.utc)
    item.revision += 1
    item.updated_at = item.deleted_at
    await db.commit()
