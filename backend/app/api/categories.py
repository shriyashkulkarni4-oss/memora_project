"""
Categories API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.models import get_db, Category, Link

router = APIRouter()


class CategoryCreate(BaseModel):
    name: str
    color: str = "#3b82f6"
    icon: str = "FolderOpen"
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    color: str
    icon: str
    description: Optional[str]
    link_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all categories for current user"""
    result = await db.execute(
        select(Category).where(Category.user_id == "user-1").order_by(Category.name)
    )
    categories = result.scalars().all()

    # Add link counts
    response = []
    for cat in categories:
        count = await db.scalar(
            select(func.count()).where(
                Link.category_id == cat.id,
                Link.is_archived == False
            )
        )
        response.append(CategoryResponse(
            id=cat.id,
            name=cat.name,
            color=cat.color,
            icon=cat.icon,
            description=cat.description,
            link_count=count or 0,
            created_at=cat.created_at,
            updated_at=cat.updated_at
        ))
    return response


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific category"""
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == "user-1")
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/", response_model=CategoryResponse)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """Create a new category"""
    category = Category(
        id=str(uuid.uuid4()),
        user_id="user-1",
        name=data.name,
        color=data.color,
        icon=data.icon,
        description=data.description
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return CategoryResponse(
        id=category.id,
        name=category.name,
        color=category.color,
        icon=category.icon,
        description=category.description,
        link_count=0,
        created_at=category.created_at,
        updated_at=category.updated_at
    )


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a category"""
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == "user-1")
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}")
async def delete_category(category_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a category"""
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == "user-1")
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Unassign links from this category
    links_result = await db.execute(
        select(Link).where(Link.category_id == category_id)
    )
    for link in links_result.scalars():
        link.category_id = None

    await db.delete(category)
    await db.commit()
    return {"message": "Category deleted successfully"}
