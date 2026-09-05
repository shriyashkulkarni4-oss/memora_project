"""Behavioral checks for production request middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.middleware.runtime import RateLimitMiddleware, SecurityHeadersMiddleware


def test_local_rate_limit_returns_stable_error_envelope() -> None:
    limited = FastAPI()
    settings = Settings(rate_limit_per_minute=2, auth_rate_limit_per_minute=2)
    limited.add_middleware(RateLimitMiddleware, settings=settings)

    @limited.get("/limited")
    async def endpoint() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(limited) as client:
        assert client.get("/limited").status_code == 200
        assert client.get("/limited").status_code == 200
        response = client.get("/limited")

    assert response.status_code == 429
    assert response.headers["retry-after"]
    assert response.json()["error"]["code"] == "RATE_LIMITED"


def test_production_security_headers_include_hsts() -> None:
    secured = FastAPI()
    settings = Settings(
        environment="production",
        app_debug=False,
        database_url="postgresql+asyncpg://memoryhive:unique-password@db/memoryhive",
        minio_access_key="memoryhive-production",
        minio_secret_key="a-unique-object-storage-password",
        redis_url="redis://redis:6379/0",
        jwt_secret_key="a-unique-jwt-secret-that-is-long-enough",
        encryption_key="a-unique-encryption-key-that-is-long-enough",
        cors_origins=["https://memoryhive.example.com"],
        allowed_hosts=["memoryhive.example.com"],
    )
    secured.add_middleware(SecurityHeadersMiddleware, settings=settings)

    @secured.get("/")
    async def endpoint() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(secured) as client:
        response = client.get("/")

    assert response.headers["strict-transport-security"].startswith("max-age=")
