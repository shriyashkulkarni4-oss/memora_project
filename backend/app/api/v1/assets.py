"""Private asset access endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import Asset, Item
from app.schemas.common import ErrorResponse
from app.services.storage import StorageService, get_storage_service

router = APIRouter()
Storage = Annotated[StorageService, Depends(get_storage_service)]
ERRORS = {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}


@router.get("/{asset_id}/download", responses=ERRORS)
async def download_asset(
    asset_id: str,
    current_user: CurrentUser,
    db: DbSession,
    storage: Storage,
) -> RedirectResponse:
    asset = await db.scalar(
        select(Asset)
        .join(Item, Item.id == Asset.item_id)
        .where(
            Asset.id == asset_id,
            Asset.user_id == current_user.id,
            Item.user_id == current_user.id,
            Item.deleted_at.is_(None),
        )
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    download_url = storage.get_file_url(asset.object_key, expires_in=300)
    if not download_url:
        raise HTTPException(status_code=404, detail="Asset is unavailable")
    return RedirectResponse(download_url, status_code=307)
