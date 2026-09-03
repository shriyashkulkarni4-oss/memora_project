"""User-owned category endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession
from app.models import Category, Item
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import ErrorResponse

router = APIRouter()
ERRORS = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


async def _owned_category(db: DbSession, user_id: str, category_id: str) -> Category:
    category = await db.scalar(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


async def _response(db: DbSession, category: Category) -> CategoryResponse:
    count = await db.scalar(
        select(func.count())
        .select_from(Item)
        .where(
            Item.user_id == category.user_id,
            Item.category_id == category.id,
            Item.deleted_at.is_(None),
        )
    )
    return CategoryResponse(
        id=category.id,
        name=category.name,
        color=category.color,
        icon=category.icon,
        description=category.description,
        item_count=count or 0,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.get("", response_model=list[CategoryResponse], responses=ERRORS)
async def list_categories(
    current_user: CurrentUser, db: DbSession
) -> list[CategoryResponse]:
    categories = (
        await db.scalars(
            select(Category)
            .where(Category.user_id == current_user.id)
            .order_by(Category.name)
        )
    ).all()
    return [await _response(db, category) for category in categories]


@router.post("", response_model=CategoryResponse, status_code=201, responses=ERRORS)
async def create_category(
    data: CategoryCreate, current_user: CurrentUser, db: DbSession
) -> CategoryResponse:
    category = Category(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=data.name,
        color=data.color,
        icon=data.icon,
        description=data.description,
    )
    db.add(category)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Category already exists") from exc
    await db.refresh(category)
    return await _response(db, category)


@router.get("/{category_id}", response_model=CategoryResponse, responses=ERRORS)
async def get_category(
    category_id: str, current_user: CurrentUser, db: DbSession
) -> CategoryResponse:
    return await _response(db, await _owned_category(db, current_user.id, category_id))


@router.patch("/{category_id}", response_model=CategoryResponse, responses=ERRORS)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> CategoryResponse:
    category = await _owned_category(db, current_user.id, category_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "name" and value is not None:
            value = " ".join(value.split())
        setattr(category, key, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Category already exists") from exc
    await db.refresh(category)
    return await _response(db, category)


@router.delete(
    "/{category_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS
)
async def delete_category(
    category_id: str, current_user: CurrentUser, db: DbSession
) -> None:
    category = await _owned_category(db, current_user.id, category_id)
    await db.execute(
        update(Item)
        .where(Item.user_id == current_user.id, Item.category_id == category.id)
        .values(category_id=None)
    )
    await db.delete(category)
    await db.commit()
