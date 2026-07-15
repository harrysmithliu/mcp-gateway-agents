from backend.mcp_gateway.registry import build_default_registry
from backend.retrieval.service import RetrievalService
from backend.retrieval.contracts import (
    RetrievalChunk,
    RetrievalCitation,
    RetrievalContext,
    RetrievalMetadata,
    RetrievalQuery,
)


class FakeRetrievalService:
    def __init__(self) -> None:
        self.received_query: RetrievalQuery | None = None

    def retrieve(self, query: RetrievalQuery) -> RetrievalContext:
        self.received_query = query
        return RetrievalContext(
            rag_enabled=True,
            retrieval_source="postgresql_pgvector",
            retrieved_chunks=[
                RetrievalChunk(
                    document_id="doc-1",
                    title="Trading Policy",
                    summary="Escalate suspicious activity.",
                    chunk_id="chunk-1",
                    chunk_index=2,
                    source_path="data/trading.md",
                    score=0.91,
                )
            ],
            citations=[
                RetrievalCitation(
                    document_id="doc-1",
                    title="Trading Policy",
                    chunk_id="chunk-1",
                    chunk_index=2,
                    source_path="data/trading.md",
                    score=0.91,
                    excerpt="Escalate suspicious activity.",
                )
            ],
            metadata=RetrievalMetadata(
                provider="local_sentence_transformer",
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                vector_dimensions=384,
                top_k=query.top_k,
                result_count=1,
                filters={"access_level": query.access_level},
            ),
        )


class FailingRetrievalService:
    def retrieve(self, query: RetrievalQuery) -> RetrievalContext:
        return RetrievalContext(
            rag_enabled=False,
            retrieval_source="postgresql_pgvector",
            metadata=RetrievalMetadata(
                top_k=query.top_k,
                status="failed",
                failure_reason="ConnectionError",
            ),
        )


def test_knowledge_search_tool_uses_shared_retrieval_service_contract() -> None:
    retrieval_service = FakeRetrievalService()
    registry = build_default_registry(retrieval_service=retrieval_service)

    result = registry.invoke(
        tool_name="knowledge.search",
        request_payload={
            "query": "policy evidence",
            "top_k": 4,
            "access_level": "internal",
            "jurisdiction": "global",
            "tags": ["policy", "trading"],
        },
    )

    assert retrieval_service.received_query == RetrievalQuery(
        text="policy evidence",
        top_k=4,
        access_level="internal",
        jurisdiction="global",
        tags=("policy", "trading"),
    )
    assert result.invocation_status == "completed"
    assert result.response_payload["query"] == "policy evidence"
    assert result.response_payload["contract_version"] == "knowledge.search/v1"
    assert result.response_payload["result_status"] == "completed"
    assert result.response_payload["total_matches"] == 1
    assert result.response_payload["retrieval_source"] == "postgresql_pgvector"
    assert result.response_payload["citations"][0]["chunk_id"] == "chunk-1"


def test_knowledge_search_tool_exposes_retrieval_failure_status() -> None:
    registry = build_default_registry(retrieval_service=FailingRetrievalService())

    result = registry.invoke(
        tool_name="knowledge.search",
        request_payload={"query": "policy evidence"},
    )

    assert result.invocation_status == "failed"
    assert result.response_payload["result_status"] == "failed"
    assert result.response_payload["retrieval_metadata"]["status"] == "failed"
    assert (
        result.response_payload["retrieval_metadata"]["failure_reason"]
        == "ConnectionError"
    )


def test_knowledge_search_tool_exposes_stable_disabled_contract() -> None:
    registry = build_default_registry(
        retrieval_service=RetrievalService(enabled=False),
    )

    result = registry.invoke(
        tool_name="knowledge.search",
        request_payload={"query": "policy evidence"},
    )

    assert result.invocation_status == "unavailable"
    assert result.response_payload["contract_version"] == "knowledge.search/v1"
    assert result.response_payload["result_status"] == "disabled"
    assert result.response_payload["total_matches"] == 0
    assert result.response_payload["citations"] == []


def test_knowledge_search_prefers_server_authorization_context_over_client_filter() -> None:
    retrieval_service = FakeRetrievalService()
    registry = build_default_registry(retrieval_service=retrieval_service)

    registry.invoke(
        tool_name="knowledge.search",
        request_payload={
            "query": "policy evidence",
            "access_level": "restricted",
            "authorization_context": {"access_level": "internal"},
        },
    )

    assert retrieval_service.received_query is not None
    assert retrieval_service.received_query.access_level == "internal"


def test_admin_scope_includes_internal_and_restricted_without_client_override() -> None:
    retrieval_service = FakeRetrievalService()
    registry = build_default_registry(retrieval_service=retrieval_service)

    registry.invoke(
        tool_name="knowledge.search",
        request_payload={
            "query": "policy evidence",
            "access_level": "restricted",
            "authorization_context": {
                "access_level": "restricted",
                "allowed_access_levels": ["internal", "restricted"],
            },
        },
    )

    assert retrieval_service.received_query is not None
    assert retrieval_service.received_query.access_level is None
    assert retrieval_service.received_query.allowed_access_levels == (
        "internal",
        "restricted",
    )
