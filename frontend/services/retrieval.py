from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RetrievalCitation:
    document_id: str
    title: str
    chunk_id: str | None = None
    chunk_index: int | None = None
    source_path: str | None = None
    score: float | None = None
    excerpt: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalChunk:
    document_id: str
    title: str
    summary: str
    chunk_id: str | None = None
    chunk_index: int | None = None
    source_path: str | None = None
    score: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalMetadata:
    provider: str | None = None
    model_name: str | None = None
    vector_dimensions: int | None = None
    top_k: int = 0
    result_count: int = 0
    filters: dict[str, object] = field(default_factory=dict)
    status: str = "completed"
    latency_ms: int = 0
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalEvidence:
    query: str | None = None
    retrieval_source: str | None = None
    citations: list[RetrievalCitation] = field(default_factory=list)
    retrieved_chunks: list[RetrievalChunk] = field(default_factory=list)
    metadata: RetrievalMetadata = field(default_factory=RetrievalMetadata)


def parse_retrieval_citations(payload: object) -> list[RetrievalCitation]:
    if not isinstance(payload, list):
        return []

    citations: list[RetrievalCitation] = []
    for item in payload:
        citation = _parse_citation(item)
        if citation is not None:
            citations.append(citation)
    return citations


def parse_retrieval_evidence(payload: dict[str, object]) -> RetrievalEvidence:
    metadata_payload = payload.get("retrieval_metadata")
    metadata = _parse_metadata(metadata_payload)
    return RetrievalEvidence(
        query=_optional_string(payload.get("query")),
        retrieval_source=_optional_string(payload.get("retrieval_source")),
        citations=parse_retrieval_citations(payload.get("citations")),
        retrieved_chunks=_parse_chunks(payload.get("retrieved_chunks")),
        metadata=metadata,
    )


def _parse_citation(payload: object) -> RetrievalCitation | None:
    if not isinstance(payload, dict):
        return None

    document_id = _optional_string(payload.get("document_id"))
    title = _optional_string(payload.get("title"))
    if not document_id or not title:
        return None
    return RetrievalCitation(
        document_id=document_id,
        title=title,
        chunk_id=_optional_string(payload.get("chunk_id")),
        chunk_index=_optional_int(payload.get("chunk_index")),
        source_path=_optional_string(payload.get("source_path")),
        score=_optional_float(payload.get("score")),
        excerpt=_optional_string(payload.get("excerpt")),
    )


def _parse_chunks(payload: object) -> list[RetrievalChunk]:
    if not isinstance(payload, list):
        return []

    chunks: list[RetrievalChunk] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        document_id = _optional_string(item.get("document_id"))
        title = _optional_string(item.get("title"))
        summary = _optional_string(item.get("summary"))
        if not document_id or not title or summary is None:
            continue
        metadata = item.get("metadata")
        chunks.append(
            RetrievalChunk(
                document_id=document_id,
                title=title,
                summary=summary,
                chunk_id=_optional_string(item.get("chunk_id")),
                chunk_index=_optional_int(item.get("chunk_index")),
                source_path=_optional_string(item.get("source_path")),
                score=_optional_float(item.get("score")),
                metadata=dict(metadata) if isinstance(metadata, dict) else {},
            )
        )
    return chunks


def _parse_metadata(payload: object) -> RetrievalMetadata:
    if not isinstance(payload, dict):
        return RetrievalMetadata()
    filters = payload.get("filters")
    return RetrievalMetadata(
        provider=_optional_string(payload.get("provider")),
        model_name=_optional_string(payload.get("model_name")),
        vector_dimensions=_optional_int(payload.get("vector_dimensions")),
        top_k=_optional_int(payload.get("top_k")) or 0,
        result_count=_optional_int(payload.get("result_count")) or 0,
        filters=dict(filters) if isinstance(filters, dict) else {},
        status=_optional_string(payload.get("status")) or "completed",
        latency_ms=_optional_int(payload.get("latency_ms")) or 0,
        failure_reason=_optional_string(payload.get("failure_reason")),
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
