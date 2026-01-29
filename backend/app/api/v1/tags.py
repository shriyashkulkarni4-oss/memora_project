"""Tags API endpoints."""

import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import DbSession
from app.models.models import Tag, link_tags
from app.schemas.tag import TagCreate, TagResponse

router = APIRouter()


@router.get("/", response_model=List[TagResponse])
async def get_tags(db: DbSession):
    """Get all tags with usage counts."""
    result = await db.execute(select(Tag).order_by(Tag.name))
    tags = result.scalars().all()

    response = []
    for tag in tags:
        count = await db.scalar(
            select(func.count()).select_from(link_tags).where(link_tags.c.tag_id == tag.id)
        )
        response.append(
            TagResponse(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                usage_count=count or 0,
            )
        )

    return sorted(response, key=lambda x: x.usage_count, reverse=True)


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(data: TagCreate, db: DbSession):
    """Create a new tag."""
    # Check if tag exists
    result = await db.execute(select(Tag).where(Tag.name == data.name.lower()))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag already exists",
        )

    # Create tag
    tag = Tag(
        id=str(uuid.uuid4()),
        name=data.name.lower(),
        color=data.color,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return TagResponse(id=tag.id, name=tag.name, color=tag.color, usage_count=0)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: str, db: DbSession):
    """Delete a tag."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )

    await db.delete(tag)
    await db.commit()
