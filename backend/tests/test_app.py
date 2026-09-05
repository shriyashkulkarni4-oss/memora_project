"""Baseline tests for application startup and API wiring."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import app
from app.services.storage import get_storage_service


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == "0.1.0"
    assert payload["environment"] in {"development", "staging", "production"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-request-id"]


def test_metrics_endpoint_exposes_request_metrics() -> None:
    with TestClient(app) as client:
        client.get("/health")
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "memoryhive_http_requests_total" in response.text


def test_development_cors_allows_expo_and_private_network_origins() -> None:
    with TestClient(app) as client:
        expo = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:8083",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        lan = client.options(
            "/api/v1/auth/login",
            headers={
                "Host": "192.168.1.24:8000",
                "Origin": "http://192.168.1.24:8083",
                "Access-Control-Request-Method": "POST",
            },
        )
        public = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://malicious.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert expo.status_code == 200
    assert expo.headers["access-control-allow-origin"] == "http://localhost:8083"
    assert lan.status_code == 200
    assert lan.headers["access-control-allow-origin"] == "http://192.168.1.24:8083"
    assert public.status_code == 400


def test_production_settings_reject_development_secrets() -> None:
    with pytest.raises(ValidationError, match="APP_DEBUG must be false"):
        Settings(environment="production")


def test_production_settings_accept_hardened_configuration() -> None:
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

    assert settings.is_production


def test_auth_routes_are_mounted_under_v1() -> None:
    paths = app.openapi()["paths"]

    assert "post" in paths["/api/v1/auth/register"]
    assert "post" in paths["/api/v1/auth/login"]
    assert "get" in paths["/api/v1/auth/me"]
    assert all(not path.startswith("/api/auth") for path in paths)


def test_auth_me_requires_bearer_token() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Not authenticated",
            "details": None,
        }
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_app_import_does_not_initialize_storage() -> None:
    assert get_storage_service.cache_info().currsize == 0
