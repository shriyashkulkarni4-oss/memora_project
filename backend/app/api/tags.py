"""
Tags API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel
import uuid

from app.models import get_db, Tag, link_tags

router = APIRouter()


class TagCreate(BaseModel):
    name: str
    color: str = "#6b7280"


class TagResponse(BaseModel):
    id: str
    name: str
    color: str
    usage_count: int = 0

    class Config:
        from_attributes = True


@router.get("/", response_model=List[TagResponse])
async def get_tags(db: AsyncSession = Depends(get_db)):
    """Get all tags with usage counts"""
    result = await db.execute(select(Tag).order_by(Tag.name))
    tags = result.scalars().all()

    response = []
    for tag in tags:
        count = await db.scalar(
            select(func.count()).select_from(link_tags).where(link_tags.c.tag_id == tag.id)
        )
        response.append(TagResponse(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            usage_count=count or 0
        ))

    return sorted(response, key=lambda x: x.usage_count, reverse=True)


@router.post("/", response_model=TagResponse)
async def create_tag(data: TagCreate, db: AsyncSession = Depends(get_db)):
    """Create a new tag"""
    # Check if tag exists
    result = await db.execute(
        select(Tag).where(Tag.name == data.name.lower())
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag = Tag(
        id=str(uuid.uuid4()),
        name=data.name.lower(),
        color=data.color
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return TagResponse(id=tag.id, name=tag.name, color=tag.color, usage_count=0)


@router.delete("/{tag_id}")
async def delete_tag(tag_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a tag"""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    await db.delete(tag)
    await db.commit()
    return {"message": "Tag deleted successfully"}
