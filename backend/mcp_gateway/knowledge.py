from backend.retrieval.contracts import RetrievalResult


KNOWLEDGE_SEARCH_CONTRACT_VERSION = "knowledge.search/v1"


def build_normalized_knowledge_payload(
    query_text: str,
    retrieval_result: RetrievalResult,
) -> dict[str, object]:
    """Build the semantic result shared by registry, HTTP and MCP transports."""

    payload = retrieval_result.to_payload()
    metadata = payload.get("retrieval_metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    result_count = int(metadata.get("result_count", 0) or 0)
    return {
        "contract_version": KNOWLEDGE_SEARCH_CONTRACT_VERSION,
        "query": query_text,
        "result_status": str(metadata.get("status", "completed")),
        "total_matches": result_count,
        **payload,
    }


def build_preview_knowledge_payload(
    query_text: str,
    preview_payload: dict[str, object],
) -> dict[str, object]:
    """Normalize the local demo knowledge path without claiming RAG grounding."""

    raw_matches = preview_payload.get("matches")
    matches = raw_matches if isinstance(raw_matches, list) else []
    result_count = len(matches)
    return {
        "contract_version": KNOWLEDGE_SEARCH_CONTRACT_VERSION,
        "query": query_text,
        "result_status": "preview",
        "total_matches": result_count,
        "rag_enabled": False,
        "retrieval_source": "knowledge_preview",
        "retrieved_chunks": [],
        "citations": [],
        "retrieval_metadata": {
            "status": "preview",
            "result_count": result_count,
        },
        "matches": matches,
    }


def build_knowledge_invocation_status(result_status: str) -> str:
    if result_status == "failed":
        return "failed"
    if result_status in {"disabled", "unavailable"}:
        return "unavailable"
    return "completed"


def is_knowledge_result_usable(
    invocation_status: str,
    response_payload: dict[str, object],
) -> bool:
    """Return whether a knowledge result is safe to expose as grounded evidence."""

    if invocation_status != "completed":
        return False
    result_status = response_payload.get("result_status")
    if isinstance(result_status, str) and result_status != "completed":
        return False
    metadata = response_payload.get("retrieval_metadata")
    if isinstance(metadata, dict):
        metadata_status = metadata.get("status")
        if isinstance(metadata_status, str) and metadata_status != "completed":
            return False
    return True
