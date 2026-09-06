"""Item analysis state and Temporal-ready helper tests."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import AnalysisStatus, Item, ItemType, ProcessingStatus, User
from app.services.analysis import run_item_analysis
from app.services.processing import ProcessingInput, ProcessingResult

pytestmark = pytest.mark.asyncio


class TextProcessor:
    async def process(self, value: ProcessingInput) -> ProcessingResult:
        assert value.item_type == ItemType.TEXT
        extracted = value.raw_text or ""
        return ProcessingResult(
            extracted_text=extracted,
            normalized_text=extracted.casefold(),
            language="en",
            summary="A generated text summary.",
        )


class FailingProcessor:
    async def process(self, _value: ProcessingInput) -> ProcessingResult:
        raise RuntimeError("analysis dependency unavailable")


async def analysis_database(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'analysis.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        user = User(id="user-1", email="analysis@example.com", hashed_password="hash")
        text_item = Item(
            id="text-1",
            user_id=user.id,
            type=ItemType.TEXT,
            raw_text="Temporal should analyze text captures that legacy OCR skips.",
            title="Text analysis",
            processing_status=ProcessingStatus.READY,
            analysis_status=AnalysisStatus.PENDING,
            analysis_version=1,
        )
        link_item = Item(
            id="link-1",
            user_id=user.id,
            type=ItemType.LINK,
            url="https://example.com/fail",
            normalized_url="https://example.com/fail",
            processing_status=ProcessingStatus.PENDING,
            analysis_status=AnalysisStatus.PENDING,
            analysis_version=2,
        )
        session.add_all([user, text_item, link_item])
        await session.commit()
    return engine, factory


async def test_text_item_analysis_updates_summary_and_state(tmp_path: Path) -> None:
    engine, factory = await analysis_database(tmp_path)

    outcome = await run_item_analysis(factory, TextProcessor(), "text-1", 1)  # type: ignore[arg-type]

    assert outcome.status == "analyzed"
    assert outcome.summary_generated is True
    async with factory() as session:
        item = await session.get(Item, "text-1")
        assert item
        assert item.analysis_status == AnalysisStatus.ANALYZED
        assert item.summary == "A generated text summary."
        assert item.normalized_text == item.raw_text.casefold()
        assert item.processing_status == ProcessingStatus.READY
        assert (
            item.item_metadata
            and item.item_metadata["analysis"]["engine"] == "temporal"
        )
    await engine.dispose()


async def test_analysis_failure_marks_item_failed(tmp_path: Path) -> None:
    engine, factory = await analysis_database(tmp_path)

    with pytest.raises(RuntimeError, match="analysis dependency unavailable"):
        await run_item_analysis(factory, FailingProcessor(), "link-1", 2)  # type: ignore[arg-type]

    async with factory() as session:
        item = await session.get(Item, "link-1")
        assert item
        assert item.analysis_status == AnalysisStatus.FAILED
        assert item.analysis_error == "analysis dependency unavailable"
        assert item.processing_status == ProcessingStatus.FAILED
        assert item.processing_error == "analysis dependency unavailable"
    await engine.dispose()


async def test_stale_analysis_version_does_not_overwrite_item(tmp_path: Path) -> None:
    engine, factory = await analysis_database(tmp_path)

    outcome = await run_item_analysis(factory, TextProcessor(), "text-1", 99)  # type: ignore[arg-type]

    assert outcome.status == "skipped"
    assert outcome.message == "Analysis request is stale"
    async with factory() as session:
        item = await session.get(Item, "text-1")
        assert item
        assert item.analysis_status == AnalysisStatus.PENDING
        assert item.summary is None
    await engine.dispose()
