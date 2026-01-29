"""API v1 Router - aggregates all route handlers."""

from fastapi import APIRouter

from app.api.v1 import auth, categories, links, tags

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(links.router, prefix="/links", tags=["Links"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(tags.router, prefix="/tags", tags=["Tags"])
