"""Document processing, multi-page PDF text extraction, OCR fallback, tagging, and search tests."""

from io import BytesIO

import pytest
from httpx import AsyncClient
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ItemType
from app.services.processing import (
    ContentProcessor,
    ProcessingInput,
)
from app.services.processing_worker import ProcessingWorker
from tests.conftest import FakeStorage
from tests.test_core_api import register_and_login

pytestmark = pytest.mark.asyncio


class MemoryStorage:
    def __init__(self, content: bytes = b"") -> None:
        self.content = content

    def get_file_bytes(self, _key: str) -> bytes:
        return self.content


def _create_blank_pdf(
    num_pages: int = 1, title: str | None = None, author: str | None = None
) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=200, height=200)
    meta = {}
    if title:
        meta["/Title"] = title
    if author:
        meta["/Author"] = author
    if meta:
        writer.add_metadata(meta)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


async def test_text_document_extraction() -> None:
    content = (
        b"This is a software design specification for the personal knowledge vault."
    )
    processor = ContentProcessor(MemoryStorage(content))  # type: ignore[arg-type]
    result = await processor.process(
        ProcessingInput("item-doc-1", ItemType.DOCUMENT, None, ["spec.txt"])
    )

    assert result.extracted_text == (
        "This is a software design specification for the personal knowledge vault."
    )
    assert result.normalized_text == result.extracted_text.casefold()
    assert result.language == "en"
    assert result.metadata["document_type"] == "text"


async def test_scanned_multipage_pdf_ocr_fallback() -> None:
    pdf_bytes = _create_blank_pdf(
        num_pages=2, title="Scanned Invoice Archive", author="Accounting Dept"
    )

    ocr_calls = []

    def mock_ocr(image: Image.Image) -> str:
        call_num = len(ocr_calls) + 1
        ocr_calls.append(call_num)
        return f"Page {call_num} invoice total USD 1250 details for vendor Alpha."

    processor = ContentProcessor(
        MemoryStorage(pdf_bytes),  # type: ignore[arg-type]
        ocr=mock_ocr,
    )
    result = await processor.process(
        ProcessingInput("item-doc-2", ItemType.DOCUMENT, None, ["invoice.pdf"])
    )

    assert result.title == "Scanned Invoice Archive"
    assert result.author == "Accounting Dept"
    assert len(ocr_calls) == 2
    assert "Page 1 invoice total USD 1250" in (result.extracted_text or "")
    assert "Page 2 invoice total USD 1250" in (result.extracted_text or "")
    assert result.metadata["document_type"] == "pdf"
    assert result.metadata["total_pages"] == 2
    assert result.metadata["ocr_pages"] == 2
    assert result.metadata["ocr_engine"] == "tesseract"


async def test_create_document_api_endpoint(
    api_client: tuple[AsyncClient, FakeStorage],
) -> None:
    client, _storage = api_client
    _user, auth_headers = await register_and_login(client, email="docuser@example.com")
    pdf_bytes = _create_blank_pdf(num_pages=1, title="Quarterly Financials")

    files = {"file": ("report.pdf", pdf_bytes, "application/pdf")}
    data = {
        "title": "Quarterly Financials Report",
        "notes": "Q3 review notes",
        "tags": "finance,quarterly,accounting",
    }

    response = await client.post(
        "/api/v1/items/document",
        headers=auth_headers,
        data=data,
        files=files,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["type"] == "document"
    assert payload["title"] == "Quarterly Financials Report"
    assert payload["notes"] == "Q3 review notes"
    assert payload["processing_status"] == "pending"
    assert len(payload["assets"]) == 1
    assert payload["assets"][0]["mime_type"] == "application/pdf"
    tag_names = {t["name"] for t in payload["tags"]}
    assert "finance" in tag_names
    assert "quarterly" in tag_names
    assert "accounting" in tag_names


async def test_document_end_to_end_ocr_worker_and_search(
    api_client_with_db: tuple[
        AsyncClient, FakeStorage, async_sessionmaker[AsyncSession]
    ],
) -> None:
    client, storage, session_factory = api_client_with_db
    _user, auth_headers = await register_and_login(client, email="e2e_doc@example.com")
    pdf_bytes = _create_blank_pdf(num_pages=1, title="Medical Lab Results")

    # 1. Upload document
    upload_res = await client.post(
        "/api/v1/items/document",
        headers=auth_headers,
        data={"title": "Blood Test Panel", "tags": "health,medical"},
        files={"file": ("lab_report.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 201
    item_id = upload_res.json()["id"]

    # 2. Run processing worker with OCR
    processor = ContentProcessor(
        storage,
        ocr=lambda _img: "Comprehensive metabolic panel showing normal glucose and electrolytes.",
    )
    worker = ProcessingWorker(session_factory, processor)
    claimed = await worker.run_once()
    assert claimed is True

    # 3. Verify item details updated with extracted text and ready status
    detail_res = await client.get(f"/api/v1/items/{item_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    item_data = detail_res.json()
    assert item_data["processing_status"] == "ready"
    assert item_data["analysis_status"] == "analyzed"
    assert "glucose and electrolytes" in item_data["extracted_text"]

    # 4. Search for document by extracted OCR content
    search_res = await client.get(
        "/api/v1/items",
        params={"q": "glucose"},
        headers=auth_headers,
    )
    assert search_res.status_code == 200
    search_items = search_res.json()["items"]
    assert len(search_items) == 1
    assert search_items[0]["id"] == item_id
