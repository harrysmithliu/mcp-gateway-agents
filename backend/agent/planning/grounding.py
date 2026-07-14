from typing import Any


DEFAULT_MAX_GROUNDED_CHUNKS = 2
DEFAULT_MAX_CHARS_PER_CHUNK = 400
DEFAULT_MAX_TOTAL_CHARS = 800


def build_grounding_context(
    retrieval_context: dict[str, object],
    max_chunks: int = DEFAULT_MAX_GROUNDED_CHUNKS,
    max_chars_per_chunk: int = DEFAULT_MAX_CHARS_PER_CHUNK,
    max_total_chars: int = DEFAULT_MAX_TOTAL_CHARS,
) -> dict[str, object]:
    """Build a bounded, traceable context payload for planner input."""

    if max_chunks <= 0 or max_chars_per_chunk <= 0 or max_total_chars <= 0:
        raise ValueError("grounding limits must be positive")

    metadata = _as_dict(retrieval_context.get("retrieval_metadata"))
    raw_chunks = retrieval_context.get("retrieved_chunks")
    raw_chunk_items = raw_chunks if isinstance(raw_chunks, list) else []
    status = _resolve_status(retrieval_context, metadata, raw_chunk_items)
    result_count = _as_int(metadata.get("result_count")) or len(raw_chunk_items)
    retrieval_source = _as_optional_string(
        retrieval_context.get("retrieval_source")
    )

    grounded_chunks: list[dict[str, object]] = []
    used_characters = 0
    truncated = False
    for raw_chunk in raw_chunk_items:
        if not isinstance(raw_chunk, dict):
            continue
        if len(grounded_chunks) >= max_chunks:
            truncated = True
            continue

        summary = _as_optional_string(raw_chunk.get("summary")) or ""
        remaining_characters = max_total_chars - used_characters
        if not summary or remaining_characters <= 0:
            truncated = True
            continue
        bounded_summary = summary[: min(max_chars_per_chunk, remaining_characters)]
        if len(bounded_summary) < len(summary):
            truncated = True
        used_characters += len(bounded_summary)

        grounded_chunks.append(
            {
                "source_reference": f"[S{len(grounded_chunks) + 1}]",
                "document_id": _as_optional_string(raw_chunk.get("document_id")),
                "title": _as_optional_string(raw_chunk.get("title")) or "Untitled",
                "summary": bounded_summary,
                "chunk_id": _as_optional_string(raw_chunk.get("chunk_id")),
                "chunk_index": _as_int(raw_chunk.get("chunk_index")),
                "source_path": _as_optional_string(raw_chunk.get("source_path")),
                "score": _as_optional_float(raw_chunk.get("score")),
            }
        )

    normalized_metadata = dict(metadata)
    normalized_metadata["result_count"] = result_count
    normalized_metadata["grounded_chunk_count"] = len(grounded_chunks)
    normalized_metadata["grounding_truncated"] = truncated
    normalized_metadata["status"] = status

    return {
        "rag_enabled": status == "completed" and bool(grounded_chunks),
        "retrieval_source": retrieval_source,
        "retrieved_chunks": grounded_chunks,
        "citations": _build_grounding_citations(
            retrieval_context.get("citations"),
            grounded_chunks,
        ),
        "retrieval_metadata": normalized_metadata,
        "grounding": {
            "status": status,
            "retrieval_source": retrieval_source,
            "result_count": result_count,
            "included_chunk_count": len(grounded_chunks),
            "max_chunks": max_chunks,
            "max_chars_per_chunk": max_chars_per_chunk,
            "max_total_chars": max_total_chars,
            "truncated": truncated,
            "character_count": used_characters,
        },
    }


def _build_grounding_citations(
    raw_citations: object,
    grounded_chunks: list[dict[str, object]],
) -> list[dict[str, object]]:
    if not isinstance(raw_citations, list):
        return []
    grounded_chunk_ids = {
        chunk.get("chunk_id")
        for chunk in grounded_chunks
        if chunk.get("chunk_id") is not None
    }
    citations: list[dict[str, object]] = []
    for raw_citation in raw_citations:
        if not isinstance(raw_citation, dict):
            continue
        chunk_id = raw_citation.get("chunk_id")
        if grounded_chunk_ids and chunk_id not in grounded_chunk_ids:
            continue
        citations.append(
            {
                "document_id": _as_optional_string(raw_citation.get("document_id")),
                "title": _as_optional_string(raw_citation.get("title")),
                "chunk_id": _as_optional_string(chunk_id),
                "chunk_index": _as_int(raw_citation.get("chunk_index")),
                "source_path": _as_optional_string(raw_citation.get("source_path")),
                "score": _as_optional_float(raw_citation.get("score")),
            }
        )
    return citations


def _resolve_status(
    retrieval_context: dict[str, object],
    metadata: dict[str, object],
    raw_chunks: list[Any],
) -> str:
    status = _as_optional_string(metadata.get("status"))
    if status:
        return status
    if retrieval_context.get("rag_enabled") and raw_chunks:
        return "completed"
    return "empty"


def _as_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _as_optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
