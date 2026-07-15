from backend.mcp_gateway.knowledge import (
    build_preview_knowledge_payload,
    build_knowledge_invocation_status,
    build_normalized_knowledge_payload,
    is_knowledge_result_usable,
)
from backend.retrieval.contracts import RetrievalMetadata, RetrievalResult


def test_normalized_knowledge_payload_is_transport_neutral() -> None:
    payload = build_normalized_knowledge_payload(
        query_text="policy evidence",
        retrieval_result=RetrievalResult(
            rag_enabled=False,
            retrieval_source="postgresql_pgvector",
            metadata=RetrievalMetadata(status="empty", result_count=0),
        ),
    )

    assert payload["contract_version"] == "knowledge.search/v1"
    assert payload["query"] == "policy evidence"
    assert payload["result_status"] == "empty"
    assert payload["total_matches"] == 0
    assert "mcp_transport" not in payload


def test_normalized_knowledge_status_maps_runtime_states() -> None:
    assert build_knowledge_invocation_status("completed") == "completed"
    assert build_knowledge_invocation_status("empty") == "completed"
    assert build_knowledge_invocation_status("disabled") == "unavailable"
    assert build_knowledge_invocation_status("unavailable") == "unavailable"
    assert build_knowledge_invocation_status("failed") == "failed"


def test_preview_knowledge_payload_is_canonical_but_not_grounded() -> None:
    payload = build_preview_knowledge_payload(
        query_text="policy evidence",
        preview_payload={"matches": [{"document_id": "demo-1"}]},
    )

    assert payload["contract_version"] == "knowledge.search/v1"
    assert payload["result_status"] == "preview"
    assert payload["retrieval_source"] == "knowledge_preview"
    assert payload["total_matches"] == 1
    assert payload["citations"] == []


def test_knowledge_result_usability_requires_completed_semantic_status() -> None:
    assert is_knowledge_result_usable(
        invocation_status="completed",
        response_payload={
            "result_status": "completed",
            "retrieval_metadata": {"status": "completed"},
        },
    ) is True
    assert is_knowledge_result_usable(
        invocation_status="unavailable",
        response_payload={"result_status": "unavailable"},
    ) is False
    assert is_knowledge_result_usable(
        invocation_status="completed",
        response_payload={"result_status": "unavailable"},
    ) is False
