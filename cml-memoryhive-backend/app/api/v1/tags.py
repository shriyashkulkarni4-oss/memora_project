"""User-owned tag endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession
from app.models import Tag, item_tags
from app.schemas.common import ErrorResponse
from app.schemas.tag import TagCreate, TagResponse, TagUpdate

router = APIRouter()
ERRORS = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


async def _owned_tag(db: DbSession, user_id: str, tag_id: str) -> Tag:
    tag = await db.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


async def _response(db: DbSession, tag: Tag) -> TagResponse:
    count = await db.scalar(
        select(func.count()).select_from(item_tags).where(item_tags.c.tag_id == tag.id)
    )
    return TagResponse(
        id=tag.id, name=tag.name, color=tag.color, usage_count=count or 0
    )


@router.get("", response_model=list[TagResponse], responses=ERRORS)
async def list_tags(current_user: CurrentUser, db: DbSession) -> list[TagResponse]:
    tags = (
        await db.scalars(
            select(Tag).where(Tag.user_id == current_user.id).order_by(Tag.name)
        )
    ).all()
    responses = [await _response(db, tag) for tag in tags]
    return sorted(responses, key=lambda tag: (-tag.usage_count, tag.name))


@router.post("", response_model=TagResponse, status_code=201, responses=ERRORS)
async def create_tag(
    data: TagCreate, current_user: CurrentUser, db: DbSession
) -> TagResponse:
    tag = Tag(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=data.name,
        color=data.color,
    )
    db.add(tag)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tag already exists") from exc
    await db.refresh(tag)
    return await _response(db, tag)


@router.patch("/{tag_id}", response_model=TagResponse, responses=ERRORS)
async def update_tag(
    tag_id: str, data: TagUpdate, current_user: CurrentUser, db: DbSession
) -> TagResponse:
    tag = await _owned_tag(db, current_user.id, tag_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "name" and value is not None:
            value = " ".join(value.lower().split())
        setattr(tag, key, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tag already exists") from exc
    await db.refresh(tag)
    return await _response(db, tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS)
async def delete_tag(tag_id: str, current_user: CurrentUser, db: DbSession) -> None:
    tag = await _owned_tag(db, current_user.id, tag_id)
    await db.delete(tag)
    await db.commit()
