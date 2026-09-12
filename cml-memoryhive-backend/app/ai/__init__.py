"""Provider-neutral AI and content-analysis contracts."""

from app.ai.contracts import (
    ANALYSIS_CONTRACT_VERSION,
    ENRICHMENT_SCHEMA_VERSION,
    AnalysisResult,
    ContentChunk,
    EmbeddingRequest,
    EmbeddingResult,
    EnrichmentRequest,
    EnrichmentResult,
    ExtractedDocument,
    ExtractionInput,
    IndexDocument,
    chunk_document,
    enrichment_result_from_payload,
    enrichment_result_to_payload,
    extracted_document_from_payload,
    extracted_document_to_payload,
)

__all__ = [
    "ANALYSIS_CONTRACT_VERSION",
    "ENRICHMENT_SCHEMA_VERSION",
    "AnalysisResult",
    "ContentChunk",
    "EmbeddingRequest",
    "EmbeddingResult",
    "EnrichmentRequest",
    "EnrichmentResult",
    "ExtractedDocument",
    "ExtractionInput",
    "IndexDocument",
    "chunk_document",
    "enrichment_result_from_payload",
    "enrichment_result_to_payload",
    "extracted_document_from_payload",
    "extracted_document_to_payload",
]
