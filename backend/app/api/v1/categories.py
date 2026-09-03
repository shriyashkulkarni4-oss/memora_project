"""Categories API endpoints."""

import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.models.models import Category, Link
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter()


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(current_user: CurrentUser, db: DbSession):
    """Get all categories for current user."""
    result = await db.execute(
        select(Category)
        .where(Category.user_id == current_user.id)
        .order_by(Category.name)
    )
    categories = result.scalars().all()

    # Add link counts
    response = []
    for cat in categories:
        count = await db.scalar(
            select(func.count()).where(
                Link.category_id == cat.id,
                Link.is_archived.is_(False),
            )
        )
        response.append(
            CategoryResponse(
                id=cat.id,
                name=cat.name,
                color=cat.color,
                icon=cat.icon,
                description=cat.description,
                link_count=count or 0,
                created_at=cat.created_at,
                updated_at=cat.updated_at,
            )
        )
    return response


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str, current_user: CurrentUser, db: DbSession):
    """Get a specific category."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == current_user.id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate, current_user: CurrentUser, db: DbSession
):
    """Create a new category."""
    category = Category(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=data.name,
        color=data.color,
        icon=data.icon,
        description=data.description,
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
        updated_at=category.updated_at,
    )


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update a category."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == current_user.id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: str, current_user: CurrentUser, db: DbSession):
    """Delete a category."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == current_user.id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Unassign links from this category
    links_result = await db.execute(select(Link).where(Link.category_id == category_id))
    for link in links_result.scalars():
        link.category_id = None

    await db.delete(category)
    await db.commit()
