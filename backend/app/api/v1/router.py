"""API v1 Router - aggregates all route handlers."""

from fastapi import APIRouter

from app.api.v1 import auth, items

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
