"""Durable item analysis helpers shared by Temporal activities and tests."""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models import (
    AIRun,
    AISuggestionFeedback,
    AISuggestionPreference,
    AnalysisStatus,
    EnrichmentRecord,
    Item,
    ItemType,
    ProcessingJob,
    ProcessingStatus,
    Tag,
    User,
)
from app.services.processing import ContentProcessor, ProcessingResult, processing_input


@dataclass(frozen=True)
class AnalysisOutcome:
    item_id: str
    status: str
    analysis_version: int
    summary_generated: bool = False
    extracted_text_length: int = 0
    message: str | None = None


def apply_processing_result(
    item: Item,
    result: ProcessingResult,
    *,
    completed_at: datetime,
    engine: str = "temporal",
) -> None:
    """Apply extracted content while preserving user-entered title/description."""
    for field in (
        "title",
        "description",
        "author",
        "published_at",
        "favicon_url",
        "extracted_text",
        "normalized_text",
        "language",
        "summary",
    ):
        value = getattr(result, field)
        preserves_user_value = field in {"title", "description"}
        preserves_prior_summary = (
            field == "summary"
            and item.summary is not None
            and not result.enrichment_succeeded
        )
        if (
            value is not None
            and not preserves_prior_summary
            and (not preserves_user_value or getattr(item, field) is None)
        ):
            setattr(item, field, value)
    item.item_metadata = {
        **(item.item_metadata or {}),
        **result.metadata,
        "analysis": {
            "engine": engine,
            "version": item.analysis_version,
            "completed_at": completed_at.isoformat(),
            "degraded": bool(result.enrichment_errors),
            "enrichment_attempted": result.enrichment_attempted,
            "enrichment_succeeded": result.enrichment_succeeded,
            "enrichment_errors": result.enrichment_errors,
        },
    }
    enrichment = item.item_metadata.get("enrichment")
    if isinstance(enrichment, dict):
        provider = enrichment.get("provider") or "deterministic"
        model = enrichment.get("model")
        source = "model" if result.enrichment_succeeded else "deterministic"
        if result.enrichment_succeeded and enrichment.get("summary"):
            if "ollama" in str(provider).lower():
                item.item_metadata["summary_attribution"] = f"Ollama generated this summary ({model})" if model else "Ollama generated this summary"
            else:
                item.item_metadata["summary_attribution"] = f"{provider} generated this summary ({model})" if model else f"{provider} generated this summary"
        else:
            item.item_metadata["summary_attribution"] = "Simple extractor generated this summary"
        provenance = {
            field: {
                "source": (
                    enrichment.get("summary_source", source)
                    if field == "summary"
                    else source
                ),
                "provider": (
                    "deterministic"
                    if field == "summary"
                    and enrichment.get("summary_source") == "deterministic"
                    else provider
                ),
                "model": (
                    None
                    if field == "summary"
                    and enrichment.get("summary_source") == "deterministic"
                    else model
                ),
                "prompt_version": (
                    "enrichment-v1"
                    if result.enrichment_succeeded
                    else "deterministic-summary-v1"
                ),
                "generated_at": completed_at.isoformat(),
            }
            for field, value in enrichment.items()
            if field
            in {
                "summary",
                "detailed_summary",
                "topics",
                "suggested_tags",
                "classification",
                "entities",
                "key_phrases",
                "content_language",
                "confidence",
                "warnings",
            }
            and value not in (None, [], "")
        }
        if not result.enrichment_succeeded and result.summary:
            provenance["summary"] = {
                "source": "deterministic",
                "provider": "deterministic",
                "model": None,
                "prompt_version": "deterministic-summary-v1",
                "generated_at": completed_at.isoformat(),
            }
        enrichment["taxonomy_version"] = 1
        enrichment["generated_at"] = completed_at.isoformat()
        enrichment["field_provenance"] = provenance
    item.analysis_status = (
        AnalysisStatus.DEGRADED if result.enrichment_errors else AnalysisStatus.ANALYZED
    )
    item.analysis_error = (
        ", ".join(result.enrichment_errors) if result.enrichment_errors else None
    )
    item.analysis_completed_at = completed_at
    item.processing_status = ProcessingStatus.READY
    item.processing_error = None
    item.revision += 1
    item.updated_at = completed_at


async def persist_enrichment_record(
    session: AsyncSession,
    item: Item,
    result: ProcessingResult,
    *,
    completed_at: datetime,
) -> EnrichmentRecord:
    """Persist one validated record per item version without overwriting history."""
    existing = await session.scalar(
        select(EnrichmentRecord).where(
            EnrichmentRecord.item_id == item.id,
            EnrichmentRecord.analysis_version == item.analysis_version,
        )
    )
    if existing:
        return existing
    metadata = result.metadata.get("enrichment", {})
    if not isinstance(metadata, dict):
        metadata = {}
    provider = str(metadata.get("provider") or "deterministic")
    latest_run = await session.scalar(
        select(AIRun)
        .where(
            AIRun.item_id == item.id,
            AIRun.analysis_version == item.analysis_version,
            AIRun.status == "completed",
            AIRun.provider == provider,
        )
        .order_by(AIRun.completed_at.desc(), AIRun.id.desc())
    )
    prompt_version = (
        latest_run.prompt_version
        if latest_run
        else (
            "enrichment-v1"
            if result.enrichment_succeeded
            else "deterministic-summary-v1"
        )
    )
    generated_at = completed_at.isoformat()
    values = {
        "summary": metadata.get("summary") or result.summary,
        "detailed_summary": metadata.get("detailed_summary"),
        "topics": list(metadata.get("topics") or []),
        "suggested_tags": list(metadata.get("suggested_tags") or []),
        "classification": metadata.get("classification"),
        "entities": list(metadata.get("entities") or []),
        "key_phrases": list(metadata.get("key_phrases") or []),
        "content_language": metadata.get("content_language") or result.language,
        "confidence": metadata.get("confidence"),
        "warnings": list(metadata.get("warnings") or []),
    }
    source = "model" if result.enrichment_succeeded else "deterministic"
    summary_source = str(metadata.get("summary_source") or source)
    field_provenance = {
        field: {
            "source": summary_source if field == "summary" else source,
            "provider": (
                "deterministic"
                if field == "summary" and summary_source == "deterministic"
                else provider if result.enrichment_succeeded else "deterministic"
            ),
            "model": (
                None
                if field == "summary" and summary_source == "deterministic"
                else metadata.get("model") if result.enrichment_succeeded else None
            ),
            "prompt_version": prompt_version,
            "generated_at": generated_at,
        }
        for field, value in values.items()
        if value not in (None, [], "")
    }
    record = EnrichmentRecord(
        user_id=item.user_id,
        item_id=item.id,
        ai_run_id=latest_run.id if latest_run else None,
        analysis_version=item.analysis_version,
        schema_version=int(metadata.get("schema_version") or 1),
        taxonomy_version=1,
        provider=provider if result.enrichment_succeeded else "deterministic",
        model=metadata.get("model") if result.enrichment_succeeded else None,
        prompt_version=prompt_version,
        content_hash=hashlib.sha256(
            (result.normalized_text or result.extracted_text or "").encode("utf-8")
        ).hexdigest(),
        field_provenance=field_provenance,
        generated_at=completed_at,
        **values,
    )
    session.add(record)
    await session.flush()
    await _auto_apply_suggestions(session, item, record)
    return record


async def _auto_apply_suggestions(
    session: AsyncSession, item: Item, record: EnrichmentRecord
) -> None:
    settings = get_settings()
    if not settings.ai_suggestions_enabled:
        return
    threshold = settings.ai_suggestion_auto_apply_threshold
    if threshold <= 0 or record.confidence is None or record.confidence < threshold:
        return
    blocked = set(
        await session.scalars(
            select(AISuggestionPreference.normalized_value).where(
                AISuggestionPreference.user_id == item.user_id,
                AISuggestionPreference.suggestion_type == "tag",
            )
        )
    )
    await session.refresh(item, attribute_names=["tags"])
    applied = dict((item.item_metadata or {}).get("ai_applied_tags") or {})
    decisions = dict((item.item_metadata or {}).get("suggestion_decisions") or {})
    changed = False
    for index, value in enumerate(record.suggested_tags):
        normalized = " ".join(value.casefold().strip().lstrip("#").split())[:50]
        if not normalized or normalized in blocked:
            continue
        tag = await session.scalar(
            select(Tag).where(Tag.user_id == item.user_id, Tag.name == normalized)
        )
        if tag is None:
            tag = Tag(user_id=item.user_id, name=normalized, color="#64748b")
            session.add(tag)
            await session.flush()
        was_present = any(existing.id == tag.id for existing in item.tags)
        feedback_id = str(uuid.uuid4())
        if not was_present:
            item.tags.append(tag)
            applied[normalized] = feedback_id
            changed = True
        session.add(
            AISuggestionFeedback(
                id=feedback_id,
                client_id=f"auto:{record.id}:{index}",
                user_id=item.user_id,
                item_id=item.id,
                enrichment_id=record.id,
                analysis_version=record.analysis_version,
                suggestion_type="tag",
                value=value,
                normalized_value=normalized,
                action="auto_accept",
                changed_item=not was_present,
                item_revision_after=item.revision,
                metadata_json={"tag_id": tag.id, "was_present": was_present},
            )
        )
        decisions[f"tag:{normalized}"] = "accept"
    if changed:
        item.item_metadata = {**(item.item_metadata or {}), "ai_applied_tags": applied}
    if record.suggested_tags:
        item.item_metadata = {
            **(item.item_metadata or {}),
            "suggestion_decisions": decisions,
        }


async def _load_item(session: AsyncSession, item_id: str) -> Item | None:
    return await session.scalar(
        select(Item)
        .options(selectinload(Item.assets))
        .where(Item.id == item_id, Item.deleted_at.is_(None))
    )


async def run_item_analysis(
    session_factory: async_sessionmaker[AsyncSession],
    processor: ContentProcessor,
    item_id: str,
    analysis_version: int | None = None,
    *,
    job_id: str | None = None,
    engine: str = "temporal",
    increment_job_attempt: bool = False,
) -> AnalysisOutcome:
    """Analyze one item idempotently for the requested analysis version."""
    async with session_factory() as session:
        item = await _load_item(session, item_id)
        if item is None:
            await _mark_job_skipped(session, job_id, "Item not found")
            await session.commit()
            return AnalysisOutcome(
                item_id, AnalysisStatus.SKIPPED.value, 0, message="Item not found"
            )
        if analysis_version is not None and item.analysis_version != analysis_version:
            await _mark_job_skipped(session, job_id, "Analysis request is stale")
            await session.commit()
            return AnalysisOutcome(
                item_id,
                AnalysisStatus.SKIPPED.value,
                item.analysis_version,
                message="Analysis request is stale",
            )
        item.analysis_status = AnalysisStatus.ANALYZING
        item.analysis_started_at = datetime.now(timezone.utc)
        item.analysis_error = None
        job = None
        if job_id:
            job = await session.get(ProcessingJob, job_id)
            if job:
                job.status = "processing"
                job.locked_at = item.analysis_started_at
                job.updated_at = item.analysis_started_at
                if increment_job_attempt:
                    job.attempts += 1
        if ItemType(item.type) != ItemType.TEXT:
            item.processing_status = ProcessingStatus.PROCESSING
            item.processing_error = None
        item._existing_tag_names = tuple(
            await session.scalars(select(Tag.name).where(Tag.user_id == item.user_id))
        )
        item._external_ai_allowed = bool(
            await session.scalar(
                select(User.ai_external_processing_allowed).where(
                    User.id == item.user_id
                )
            )
        )
        payload = processing_input(item, job)
        await session.commit()

    try:
        result = await processor.process(payload)
    except Exception as exc:
        await mark_analysis_failed(
            session_factory,
            item_id,
            analysis_version,
            str(exc),
            job_id=job_id,
        )
        raise

    completed_at = datetime.now(timezone.utc)
    async with session_factory() as session:
        item = await _load_item(session, item_id)
        if item is None:
            await _mark_job_skipped(session, job_id, "Item not found")
            await session.commit()
            return AnalysisOutcome(
                item_id, AnalysisStatus.SKIPPED.value, 0, message="Item not found"
            )
        if analysis_version is not None and item.analysis_version != analysis_version:
            await _mark_job_skipped(session, job_id, "Analysis request is stale")
            await session.commit()
            return AnalysisOutcome(
                item_id,
                AnalysisStatus.SKIPPED.value,
                item.analysis_version,
                message="Analysis request is stale",
            )
        apply_processing_result(item, result, completed_at=completed_at, engine=engine)
        await persist_enrichment_record(
            session, item, result, completed_at=completed_at
        )
        if job_id:
            job = await session.get(ProcessingJob, job_id)
            if job:
                job.status = "completed"
                job.locked_at = None
                job.last_error = item.analysis_error
                job.updated_at = completed_at
                job.completed_at = completed_at
        await session.commit()
        return AnalysisOutcome(
            item_id=item.id,
            status=AnalysisStatus(item.analysis_status).value,
            analysis_version=item.analysis_version,
            summary_generated=bool(item.summary),
            extracted_text_length=len(item.extracted_text or ""),
        )


async def mark_analysis_failed(
    session_factory: async_sessionmaker[AsyncSession],
    item_id: str,
    analysis_version: int | None,
    error: str,
    *,
    job_id: str | None = None,
    terminal: bool = False,
) -> None:
    async with session_factory() as session:
        item = await _load_item(session, item_id)
        if item is None:
            return
        if analysis_version is not None and item.analysis_version != analysis_version:
            return
        now = datetime.now(timezone.utc)
        job = await session.get(ProcessingJob, job_id) if job_id else None
        retrying = bool(not terminal and job and job.attempts < job.max_attempts)
        item.analysis_status = (
            AnalysisStatus.SCHEDULED
            if retrying and job and job.execution_backend == "temporal"
            else AnalysisStatus.PENDING if retrying else AnalysisStatus.FAILED
        )
        item.analysis_error = error[:4000]
        item.analysis_completed_at = None if retrying else now
        if ItemType(item.type) != ItemType.TEXT:
            item.processing_status = (
                ProcessingStatus.PENDING if retrying else ProcessingStatus.FAILED
            )
            item.processing_error = item.analysis_error
        if job:
            job.status = (
                "scheduled"
                if retrying and job.execution_backend == "temporal"
                else "pending" if retrying else "failed"
            )
            job.locked_at = None
            job.last_error = item.analysis_error
            job.updated_at = now
            job.next_attempt_at = now + timedelta(
                seconds=min(300, 2 ** max(job.attempts, 1))
            )
            job.completed_at = None if retrying else now
        item.updated_at = now
        await session.commit()


async def _mark_job_skipped(
    session: AsyncSession, job_id: str | None, message: str
) -> None:
    if not job_id:
        return
    job = await session.get(ProcessingJob, job_id)
    if not job:
        return
    now = datetime.now(timezone.utc)
    job.status = "skipped"
    job.locked_at = None
    job.last_error = message
    job.updated_at = now
    job.completed_at = now
