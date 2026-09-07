"""API v1 Router - aggregates all route handlers."""

from fastapi import APIRouter

from app.api.v1 import account, admin, assets, auth, categories, items, tags

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(tags.router, prefix="/tags", tags=["Tags"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(account.router, prefix="/account", tags=["Account"])
