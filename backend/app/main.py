"""Memoryhive FastAPI Application Entry Point."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.errors import install_error_handlers
from app.database import get_db
from app.middleware.runtime import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    configure_logging,
)

settings = get_settings()
configure_logging()
logger = logging.getLogger("memoryhive.lifecycle")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("application starting")
    yield
    logger.info("application stopped")


app = FastAPI(
    title="Memoryhive API",
    description="Mobile-first, offline-first smart bookmark & link management API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
install_error_handlers(app)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(SecurityHeadersMiddleware, settings=settings)
app.add_middleware(RateLimitMiddleware, settings=settings)
app.add_middleware(RequestContextMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Include API router with v1 prefix
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
    }


@app.get("/health/live", include_in_schema=False)
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", include_in_schema=False)
async def readiness_check(
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Memoryhive API",
        "version": "0.1.0",
        "docs": "/docs",
    }
