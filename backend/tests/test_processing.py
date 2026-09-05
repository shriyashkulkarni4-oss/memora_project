"""Content extraction, queue, retry, and SSRF regression tests."""

from pathlib import Path

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.database import Base
from app.models import Item, ItemType, ProcessingJob, ProcessingStatus, User
from app.services.processing import (
    ContentProcessor,
    ProcessingInput,
    ProcessingResult,
    SecureLinkFetcher,
    UnsafeUrlError,
)
from app.services.processing_worker import ProcessingWorker, retry_failed_item
from tests.conftest import FakeStorage
from tests.test_core_api import register_and_login

pytestmark = pytest.mark.asyncio


class MemoryStorage:
    def __init__(self, content: bytes = b"image") -> None:
        self.content = content

    def get_file_bytes(self, _key: str) -> bytes:
        return self.content


async def public_resolver(hostname: str) -> list[str]:
    assert hostname == "example.com"
    return ["93.184.216.34"]


async def test_secure_link_metadata_and_readable_text_extraction() -> None:
    html = b"""
    <html><head><title>Fallback title</title>
    <meta property="og:title" content="Reliable Systems">
    <meta name="description" content="A practical guide">
    <meta name="author" content="A. Engineer"></head>
    <body><nav>Noise</nav><article><h1>Reliable Systems</h1>
    <p>Retries need idempotency and bounded exponential backoff.</p></article></body></html>
    """
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=html,
                request=request,
            )
        )
    )
    fetcher = SecureLinkFetcher(client=client, resolver=public_resolver)
    processor = ContentProcessor(MemoryStorage(), fetcher=fetcher)  # type: ignore[arg-type]
    result = await processor.process(
        ProcessingInput("item-1", ItemType.LINK, "https://example.com/guide", [])
    )
    await client.aclose()

    assert result.title == "Reliable Systems"
    assert result.description == "A practical guide"
    assert result.author == "A. Engineer"
    assert "bounded exponential backoff" in (result.extracted_text or "")
    assert "Noise" not in (result.extracted_text or "")
    assert result.metadata["resolved_url"] == "https://example.com/guide"


async def test_link_fetcher_rejects_private_network_targets() -> None:
    fetcher = SecureLinkFetcher()
    with pytest.raises(UnsafeUrlError, match="non-public"):
        await fetcher._validate("http://127.0.0.1/internal")


async def test_screenshot_ocr_is_normalized_and_language_detected() -> None:
    from io import BytesIO

    from PIL import Image

    output = BytesIO()
    Image.new("RGB", (4, 4), "white").save(output, format="PNG")
    processor = ContentProcessor(
        MemoryStorage(output.getvalue()),  # type: ignore[arg-type]
        ocr=lambda _image: "Bonjour   tout le monde.\n\nCeci est un texte en francais.",
    )
    result = await processor.process(
        ProcessingInput("item-1", ItemType.SCREENSHOT, None, ["image.png"])
    )

    assert result.extracted_text == (
        "Bonjour tout le monde.\nCeci est un texte en francais."
    )
    assert result.normalized_text == result.extracted_text.casefold()
    assert result.language == "fr"
    assert result.metadata["ocr_engine"] == "tesseract"


class SuccessfulProcessor:
    async def process(self, _value: ProcessingInput) -> ProcessingResult:
        return ProcessingResult(
            title="Automatically extracted title",
            description="Automatically extracted description",
            extracted_text="OCR makes screenshots searchable",
            normalized_text="ocr makes screenshots searchable",
            language="en",
        )


class FailingProcessor:
    async def process(self, _value: ProcessingInput) -> ProcessingResult:
        raise RuntimeError("OCR executable unavailable")


async def processing_database(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'worker.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        user = User(id="user-1", email="worker@example.com", hashed_password="hash")
        item = Item(
            id="item-1",
            user_id=user.id,
            type=ItemType.SCREENSHOT,
            title="User-provided title",
            description="User-provided description",
            processing_status=ProcessingStatus.PENDING,
        )
        session.add_all(
            [user, item, ProcessingJob(id="job-1", item_id=item.id, kind="screenshot")]
        )
        await session.commit()
    return engine, factory


async def test_worker_completes_and_indexes_extracted_content(tmp_path: Path) -> None:
    engine, factory = await processing_database(tmp_path)
    worker = ProcessingWorker(factory, SuccessfulProcessor())  # type: ignore[arg-type]
    assert await worker.run_once() is True
    assert await worker.run_once() is False
    async with factory() as session:
        item = await session.get(Item, "item-1")
        job = await session.get(ProcessingJob, "job-1")
        assert item and item.processing_status == ProcessingStatus.READY
        assert item.title == "User-provided title"
        assert item.description == "User-provided description"
        assert item.extracted_text == "OCR makes screenshots searchable"
        assert item.revision == 2
        assert job and job.status == "completed" and job.completed_at is not None
    await engine.dispose()


async def test_exhausted_job_can_be_requeued(tmp_path: Path) -> None:
    engine, factory = await processing_database(tmp_path)
    async with factory() as session:
        job = await session.get(ProcessingJob, "job-1")
        assert job
        job.max_attempts = 1
        await session.commit()
    worker = ProcessingWorker(factory, FailingProcessor())  # type: ignore[arg-type]
    assert await worker.run_once() is True
    async with factory() as session:
        item = await session.get(Item, "item-1")
        job = await session.get(ProcessingJob, "job-1")
        assert item and item.processing_status == ProcessingStatus.FAILED
        assert item.processing_error == "OCR executable unavailable"
        assert job and job.status == "failed"
        await retry_failed_item(session, item)
        await session.commit()
        assert (
            await session.scalar(select(func.count()).select_from(ProcessingJob)) == 2
        )
        assert item.processing_status == ProcessingStatus.PENDING
    await engine.dispose()


async def test_capture_enqueues_processing_and_rejects_duplicate_retry(
    api_client: tuple[AsyncClient, FakeStorage],
) -> None:
    client, _storage = api_client
    _user, headers = await register_and_login(client, "processing-api@example.com")
    captured = await client.post(
        "/api/v1/items",
        json={"type": "link", "url": "https://example.com/queued"},
        headers=headers,
    )
    assert captured.status_code == 201
    assert captured.json()["processing_status"] == "pending"
    retry = await client.post(
        f"/api/v1/items/{captured.json()['id']}/processing/retry", headers=headers
    )
    assert retry.status_code == 409
    assert retry.json()["error"]["message"] == "Item processing is already queued"


async def test_processing_settings_have_bounded_defaults() -> None:
    settings = Settings(database_url="sqlite+aiosqlite://")
    assert settings.processing_max_attempts == 3
    assert settings.processing_fetch_max_bytes == 5 * 1024 * 1024
