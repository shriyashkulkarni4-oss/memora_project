"""Provider-independent normalization and lightweight source-grounding checks."""

import re
from dataclasses import replace

from app.ai.contracts import EnrichmentResult

TAXONOMY_VERSION = 1
CLASSIFICATIONS = frozenset(
    {"article", "reference", "research", "product", "personal", "media", "other"}
)
CLASSIFICATION_ALIASES = {
    "blog": "article",
    "blog_post": "article",
    "documentation": "reference",
    "docs": "reference",
    "paper": "research",
    "academic": "research",
    "video": "media",
    "podcast": "media",
    "bookmark": "reference",
}
STOPWORDS = frozenset(
    {
        "about",
        "after",
        "also",
        "and",
        "are",
        "because",
        "been",
        "being",
        "but",
        "can",
        "for",
        "from",
        "has",
        "have",
        "into",
        "its",
        "not",
        "that",
        "the",
        "their",
        "then",
        "there",
        "these",
        "this",
        "those",
        "was",
        "were",
        "will",
        "with",
    }
)


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w'-]+", value.casefold())
        if len(token) >= 3 and token not in STOPWORDS
    }


def faithfulness_score(value: str | None, source_tokens: set[str]) -> float:
    """Return lexical support ratio used as a conservative hallucination signal."""
    if not value:
        return 1.0
    output_tokens = _tokens(value)
    if not output_tokens:
        return 1.0
    return len(output_tokens & source_tokens) / len(output_tokens)


def _grounded_terms(
    values: tuple[str, ...], source_tokens: set[str]
) -> tuple[str, ...]:
    return tuple(value for value in values if _tokens(value) & source_tokens)


def _normalize_tags(
    values: tuple[str, ...], existing_tags: tuple[str, ...] | list[str]
) -> tuple[str, ...]:
    existing = {" ".join(value.casefold().split()): value for value in existing_tags}
    normalized: dict[str, str] = {}
    for value in values:
        key = " ".join(value.casefold().split()).strip("#")
        if not key:
            continue
        normalized.setdefault(key, existing.get(key, key))
    return tuple(normalized.values())


def normalize_enrichment(
    result: EnrichmentResult,
    *,
    source_text: str,
    content_language: str | None,
    existing_tags: tuple[str, ...] | list[str] = (),
) -> EnrichmentResult:
    """Validate taxonomy, tags, grounding, language, and safe output bounds."""
    source_tokens = _tokens(source_text)
    warnings = list(result.warnings)
    summary = result.summary
    detailed_summary = result.detailed_summary
    if faithfulness_score(summary, source_tokens) < 0.25:
        summary = None
        warnings.append("ungrounded_summary_rejected")
    if faithfulness_score(detailed_summary, source_tokens) < 0.2:
        detailed_summary = None
        warnings.append("ungrounded_detailed_summary_rejected")

    topics = _grounded_terms(tuple(result.topics), source_tokens)
    entities = _grounded_terms(tuple(result.entities), source_tokens)
    key_phrases = _grounded_terms(tuple(result.key_phrases), source_tokens)
    grounded_tags = _grounded_terms(tuple(result.suggested_tags), source_tokens)
    removed_terms = (
        len(result.topics)
        - len(topics)
        + len(result.entities)
        - len(entities)
        + len(result.key_phrases)
        - len(key_phrases)
        + len(result.suggested_tags)
        - len(grounded_tags)
    )
    if removed_terms:
        warnings.append("unsupported_terms_rejected")

    classification = (
        result.classification.casefold().replace(" ", "_")
        if result.classification
        else None
    )
    if classification:
        classification = CLASSIFICATION_ALIASES.get(classification, classification)
        if classification not in CLASSIFICATIONS:
            classification = "other"
            warnings.append("classification_normalized")
    language = (
        content_language
        if content_language
        and re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?", content_language)
        else None
    )
    if content_language and language is None:
        warnings.append("invalid_language_rejected")

    return replace(
        result,
        summary=summary,
        detailed_summary=detailed_summary,
        topics=topics,
        suggested_tags=_normalize_tags(grounded_tags, existing_tags),
        classification=classification,
        entities=entities,
        key_phrases=key_phrases,
        content_language=language,
        warnings=tuple(dict.fromkeys(warnings)),
    )
