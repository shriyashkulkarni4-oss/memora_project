"""Links API endpoints."""

import uuid
from typing import List, Optional

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
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.models.models import Link, LinkSource, LinkStatus, Tag
from app.schemas.link import (
    LinkCreate,
    LinkResponse,
    LinkStats,
    LinkUpdate,
    TagResponse,
)
from app.services.storage import StorageService, get_storage_service

router = APIRouter()


def _build_link_response(link: Link, storage: StorageService) -> LinkResponse:
    """Build LinkResponse from Link model."""
    screenshot_url = None
    if link.screenshot_data and link.screenshot_data.get("file_key"):
        screenshot_url = storage.get_file_url(link.screenshot_data["file_key"])

    return LinkResponse(
        id=link.id,
        user_id=link.user_id,
        url=link.url,
        title=link.title,
        description=link.description,
        favicon=link.favicon,
        source=link.source,
        status=link.status,
        category_id=link.category_id,
        tags=[TagResponse.model_validate(tag) for tag in link.tags],
        ai_summary=link.ai_summary,
        screenshot_url=screenshot_url,
        is_favorite=link.is_favorite,
        is_archived=link.is_archived,
        read_count=link.read_count,
        last_visited_at=link.last_visited_at,
        notes=link.notes,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


@router.get("/", response_model=List[LinkResponse])
async def get_links(
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageService = Depends(get_storage_service),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    source: Optional[LinkSource] = None,
    is_favorite: Optional[bool] = None,
    is_archived: Optional[bool] = Query(default=False),
    skip: int = 0,
    limit: int = 50,
):
    """Get all links with optional filters."""
    query = select(Link).where(Link.user_id == current_user.id)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Link.title.ilike(search_filter))
            | (Link.description.ilike(search_filter))
            | (Link.url.ilike(search_filter))
        )

    if category_id:
        query = query.where(Link.category_id == category_id)

    if source:
        query = query.where(Link.source == source)

    if is_favorite is not None:
        query = query.where(Link.is_favorite == is_favorite)

    if is_archived is not None:
        query = query.where(Link.is_archived == is_archived)

    query = query.order_by(Link.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    links = result.scalars().all()

    return [_build_link_response(link, storage) for link in links]


@router.get("/stats", response_model=LinkStats)
async def get_link_stats(current_user: CurrentUser, db: DbSession):
    """Get link statistics."""
    total = await db.scalar(
        select(func.count()).select_from(Link).where(Link.user_id == current_user.id)
    )
    favorites = await db.scalar(
        select(func.count())
        .select_from(Link)
        .where(Link.user_id == current_user.id, Link.is_favorite.is_(True))
    )
    archived = await db.scalar(
        select(func.count())
        .select_from(Link)
        .where(Link.user_id == current_user.id, Link.is_archived.is_(True))
    )
    pending = await db.scalar(
        select(func.count())
        .select_from(Link)
        .where(Link.user_id == current_user.id, Link.status == LinkStatus.PENDING)
    )

    return LinkStats(
        total_links=total or 0,
        favorite_links=favorites or 0,
        archived_links=archived or 0,
        pending_processing=pending or 0,
    )


@router.get("/{link_id}", response_model=LinkResponse)
async def get_link(
    link_id: str,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageService = Depends(get_storage_service),
):
    """Get a specific link by ID."""
    result = await db.execute(
        select(Link).where(Link.id == link_id, Link.user_id == current_user.id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )
    return _build_link_response(link, storage)


@router.post("/", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_link(
    link_data: LinkCreate,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageService = Depends(get_storage_service),
):
    """Create a new link."""
    link = Link(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        url=link_data.url,
        title=link_data.title,
        description=link_data.description,
        source=link_data.source,
        category_id=link_data.category_id,
        notes=link_data.notes,
        status=LinkStatus.PENDING,
    )

    # Handle tags
    if link_data.tags:
        for tag_name in link_data.tags:
            result = await db.execute(select(Tag).where(Tag.name == tag_name.lower()))
            tag = result.scalar_one_or_none()
            if not tag:
                tag = Tag(id=str(uuid.uuid4()), name=tag_name.lower())
                db.add(tag)
            link.tags.append(tag)

    db.add(link)
    await db.commit()
    await db.refresh(link)
    return _build_link_response(link, storage)


@router.post(
    "/screenshot", response_model=LinkResponse, status_code=status.HTTP_201_CREATED
)
async def create_screenshot_link(
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    title: str = Form(...),
    storage: StorageService = Depends(get_storage_service),
    description: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # comma-separated
    notes: Optional[str] = Form(None),
):
    """Create a new link with screenshot upload."""
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only images are allowed.",
        )

    # Upload to MinIO
    upload_result = await storage.upload_file(
        file, folder="screenshots", user_id=current_user.id
    )

    # Create link
    link = Link(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        url=None,
        title=title,
        description=description,
        source=LinkSource.SCREENSHOT,
        category_id=category_id,
        notes=notes,
        status=LinkStatus.PENDING,
        screenshot_data={
            "file_key": upload_result["file_key"],
            "file_size": upload_result["file_size"],
            "content_type": upload_result["content_type"],
            "ocr_processed": False,
        },
    )

    # Handle tags
    if tags:
        tag_names = [t.strip() for t in tags.split(",") if t.strip()]
        for tag_name in tag_names:
            result = await db.execute(select(Tag).where(Tag.name == tag_name.lower()))
            tag = result.scalar_one_or_none()
            if not tag:
                tag = Tag(id=str(uuid.uuid4()), name=tag_name.lower())
                db.add(tag)
            link.tags.append(tag)

    db.add(link)
    await db.commit()
    await db.refresh(link)
    return _build_link_response(link, storage)


@router.patch("/{link_id}", response_model=LinkResponse)
async def update_link(
    link_id: str,
    link_data: LinkUpdate,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageService = Depends(get_storage_service),
):
    """Update a link."""
    result = await db.execute(
        select(Link).where(Link.id == link_id, Link.user_id == current_user.id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    update_data = link_data.model_dump(exclude_unset=True)

    # Handle tags separately
    if "tags" in update_data:
        tag_names = update_data.pop("tags")
        link.tags = []
        for tag_name in tag_names:
            result = await db.execute(select(Tag).where(Tag.name == tag_name.lower()))
            tag = result.scalar_one_or_none()
            if not tag:
                tag = Tag(id=str(uuid.uuid4()), name=tag_name.lower())
                db.add(tag)
            link.tags.append(tag)

    for field, value in update_data.items():
        setattr(link, field, value)

    await db.commit()
    await db.refresh(link)
    return _build_link_response(link, storage)


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: str,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageService = Depends(get_storage_service),
):
    """Delete a link."""
    result = await db.execute(
        select(Link).where(Link.id == link_id, Link.user_id == current_user.id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    # Delete screenshot from storage if exists
    if link.screenshot_data and link.screenshot_data.get("file_key"):
        storage.delete_file(link.screenshot_data["file_key"])

    await db.delete(link)
    await db.commit()


@router.post("/{link_id}/favorite")
async def toggle_favorite(
    link_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Toggle favorite status."""
    result = await db.execute(
        select(Link).where(Link.id == link_id, Link.user_id == current_user.id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    link.is_favorite = not link.is_favorite
    await db.commit()
    return {"is_favorite": link.is_favorite}


@router.post("/{link_id}/archive")
async def toggle_archive(
    link_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Toggle archive status."""
    result = await db.execute(
        select(Link).where(Link.id == link_id, Link.user_id == current_user.id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    link.is_archived = not link.is_archived
    await db.commit()
    return {"is_archived": link.is_archived}
