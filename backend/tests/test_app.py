"""Baseline tests for application startup and API wiring."""

from fastapi.testclient import TestClient

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
    assert response.json() == {"detail": "Not authenticated"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_app_import_does_not_initialize_storage() -> None:
    assert get_storage_service.cache_info().currsize == 0
