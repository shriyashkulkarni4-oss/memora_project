"""Contract and migration coverage for the canonical Item model."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect

from app.main import app
from app.models import Asset, Item, ItemType, Tag
from app.schemas.item import ItemCreate


def test_item_variants_validate_required_content() -> None:
    link = ItemCreate(type=ItemType.LINK, url="https://example.com/article")
    text = ItemCreate(type=ItemType.TEXT, raw_text="A useful thought")
    screenshot = ItemCreate(type=ItemType.SCREENSHOT)

    assert str(link.url) == "https://example.com/article"
    assert text.raw_text == "A useful thought"
    assert screenshot.type == ItemType.SCREENSHOT

    with pytest.raises(ValidationError, match="url is required"):
        ItemCreate(type=ItemType.LINK)
    with pytest.raises(ValidationError, match="raw_text is required"):
        ItemCreate(type=ItemType.TEXT, raw_text="  ")


def test_item_openapi_contract_is_versioned_and_complete() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert {"get", "post"} <= set(paths["/api/v1/items"])
    assert {"get", "patch", "delete"} <= set(paths["/api/v1/items/{item_id}"])
    item_type = schema["components"]["schemas"]["ItemType"]
    assert set(item_type["enum"]) == {"link", "screenshot", "text"}
    create_schema = schema["components"]["schemas"]["ItemCreate"]
    assert {"type", "url", "raw_text", "created_at"} <= set(create_schema["properties"])


def test_validation_uses_stable_error_envelope() -> None:
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json={})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "Request validation failed"
    assert isinstance(payload["error"]["details"], list)


def test_ownership_and_uniqueness_constraints_exist() -> None:
    tag_constraints = {constraint.name for constraint in Tag.__table__.constraints}
    item_constraints = {constraint.name for constraint in Item.__table__.constraints}
    asset_constraints = {constraint.name for constraint in Asset.__table__.constraints}

    assert "uq_tags_user_name" in tag_constraints
    assert "ck_items_required_content" in item_constraints
    assert "ck_items_revision_positive" in item_constraints
    assert "uq_assets_object_key" in asset_constraints
    assert Item.__table__.c.user_id.foreign_keys
    assert Asset.__table__.c.user_id.foreign_keys


def test_migrations_upgrade_and_downgrade_clean_database(tmp_path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    environment = {**os.environ, "DATABASE_URL": database_url, "APP_DEBUG": "false"}

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        cwd=backend_dir,
        env=environment,
        capture_output=True,
        text=True,
    )
    engine = create_engine(f"sqlite:///{database_path}")
    assert {"users", "categories", "items", "assets", "tags", "item_tags"} <= set(
        inspect(engine).get_table_names()
    )
    engine.dispose()

    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        check=True,
        cwd=backend_dir,
        env=environment,
        capture_output=True,
        text=True,
    )
    engine = create_engine(f"sqlite:///{database_path}")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
