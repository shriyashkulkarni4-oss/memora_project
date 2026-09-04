"""Database-isolated API integration fixtures."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.services.storage import get_storage_service


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def upload_bytes(
        self,
        content: bytes,
        *,
        content_type: str,
        original_filename: str | None = None,
        folder: str = "screenshots",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        key = f"{folder}/{user_id}/test-object.png"
        self.objects[key] = content
        return {
            "file_key": key,
            "file_size": len(content),
            "content_type": content_type,
        }

    def get_file_url(self, file_key: str, expires_in: int = 300) -> str:
        if file_key not in self.objects:
            return ""
        return f"https://assets.example.test/{file_key}?expires={expires_in}"

    def delete_file(self, file_key: str) -> bool:
        self.objects.pop(file_key, None)
        self.deleted.append(file_key)
        return True


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[tuple[AsyncClient, FakeStorage]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_db() -> AsyncIterator[Any]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    storage = FakeStorage()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_service] = lambda: storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, storage

    app.dependency_overrides.clear()
    await engine.dispose()
