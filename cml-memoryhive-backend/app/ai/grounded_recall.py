"""Bounded, provider-neutral grounded recall with server-verified citations."""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass

from app.ai.budgets import DatabaseBudgetGuard
from app.ai.contracts import EnrichmentRequest
from app.ai.gateway import AIGateway, ProviderError, ProviderUsage
from app.ai.policy import AITask, resolve_task_policy
from app.config import Settings

_WORD = re.compile(r"[\w'-]+", re.UNICODE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass(frozen=True)
class RecallPassage:
    citation_id: int
    item_id: str
    title: str | None
    text: str


@dataclass(frozen=True)
class GroundedClaim:
    text: str
    citation_ids: tuple[int, ...]


@dataclass(frozen=True)
class GroundedRecallResult:
    answer: str
    claims: tuple[GroundedClaim, ...]
    insufficient_evidence: bool
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = None


def _tokens(value: str) -> set[str]:
    return {
        match.group(0).casefold()
        for match in _WORD.finditer(value)
        if len(match.group(0)) > 2
    }


def verify_claims(
    draft: str, passages: tuple[RecallPassage, ...], *, minimum_overlap: float
) -> tuple[GroundedClaim, ...]:
    """Attach each claim to supporting passages; reject any unsupported claim."""
    claims: list[GroundedClaim] = []
    passage_tokens = [
        (passage.citation_id, _tokens(passage.text)) for passage in passages
    ]
    for raw in _SENTENCE.split(draft.strip()):
        text = raw.strip().lstrip("-*• ")
        if not text:
            continue
        claim_tokens = _tokens(text)
        if not claim_tokens:
            continue
        scores = [
            (len(claim_tokens & source) / len(claim_tokens), citation_id)
            for citation_id, source in passage_tokens
        ]
        best_score = max((score for score, _ in scores), default=0.0)
        citations = tuple(
            citation_id
            for score, citation_id in scores
            if score == best_score and score >= minimum_overlap
        )
        if not citations:
            return ()
        claims.append(GroundedClaim(text=text, citation_ids=citations[:2]))
    return tuple(claims)


class GroundedRecallPipeline:
    def __init__(
        self,
        gateway: AIGateway,
        settings: Settings,
        budget_guard: DatabaseBudgetGuard | None = None,
    ) -> None:
        self.gateway = gateway
        self.settings = settings
        self.budget_guard = budget_guard

    async def answer(
        self,
        question: str,
        passages: tuple[RecallPassage, ...],
        *,
        user_id: str,
        external_allowed_for_user: bool = False,
    ) -> GroundedRecallResult:
        if not passages:
            return self._insufficient()
        policy = resolve_task_policy(
            self.settings,
            self.gateway,
            AITask.RECALL,
            external_allowed_for_user=external_allowed_for_user,
        )
        routes = ([policy.primary] if policy.primary else []) + list(policy.fallbacks)
        if not routes:
            return self._insufficient()
        source_text = "\n\n".join(
            f"SOURCE {p.citation_id} (saved item {p.item_id}):\n{p.text[:self.settings.ai_recall_max_passage_characters]}"
            for p in passages
        )
        prompt = (
            "Answer the QUESTION using only the SOURCES below. If they do not support an answer, "
            "return exactly INSUFFICIENT_EVIDENCE. Do not use outside knowledge. Keep each factual "
            "claim in a separate short sentence.\n\nQUESTION:\n"
            f"{question}\n\nSOURCES:\n{source_text}"
        )
        for route in routes:
            if route is None:
                continue
            reservation = None
            try:
                if self.budget_guard:
                    reservation = await self.budget_guard.reserve(
                        operation_key=f"recall:{uuid.uuid4()}",
                        user_id=user_id,
                        item_id=None,
                        task=AITask.RECALL.value,
                        provider=route.provider,
                        model=route.model,
                        estimated_tokens=max(1, len(prompt) // 4),
                    )
                started = time.perf_counter()
                response = await self.gateway.enrich(
                    route.provider,
                    EnrichmentRequest(
                        item_id=f"recall:{uuid.uuid4()}",
                        analysis_version=1,
                        text=prompt,
                        max_characters=len(prompt),
                    ),
                    model=route.model,
                )
                if reservation and self.budget_guard:
                    await self.budget_guard.complete(reservation, response.usage)
                draft = (response.enrichment.summary or "").strip()
                if not draft or draft.upper() == "INSUFFICIENT_EVIDENCE":
                    return self._insufficient()
                draft = draft[: self.settings.ai_recall_max_answer_characters]
                claims = verify_claims(
                    draft,
                    passages,
                    minimum_overlap=self.settings.ai_recall_grounding_overlap,
                )
                if not claims:
                    return self._insufficient()
                answer = " ".join(
                    f"{claim.text} {' '.join(f'[{value}]' for value in claim.citation_ids)}"
                    for claim in claims
                )
                return GroundedRecallResult(
                    answer=answer,
                    claims=claims,
                    insufficient_evidence=False,
                    provider=response.provenance.provider.value,
                    model=response.provenance.model,
                    latency_ms=int((time.perf_counter() - started) * 1_000),
                )
            except ProviderError:
                if reservation and self.budget_guard:
                    await self.budget_guard.complete(
                        reservation, ProviderUsage(), failed=True
                    )
        return self._insufficient()

    @staticmethod
    def _insufficient() -> GroundedRecallResult:
        return GroundedRecallResult(
            answer="There is not enough evidence in your saved items to answer that question.",
            claims=(),
            insufficient_evidence=True,
        )
