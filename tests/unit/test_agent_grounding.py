from backend.agent.service import AgentService
from backend.mcp_gateway.registry import build_default_registry
from backend.retrieval.contracts import (
    RetrievalChunk,
    RetrievalCitation,
    RetrievalContext,
    RetrievalMetadata,
    RetrievalQuery,
)


class GroundedRetrievalService:
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
                    source_path="data/trading.md",
                    score=0.91,
                )
            ],
            citations=[
                RetrievalCitation(
                    document_id="doc-1",
                    title="Trading Policy",
                    chunk_id="chunk-1",
                    source_path="data/trading.md",
                    score=0.91,
                )
            ],
            metadata=RetrievalMetadata(
                provider="mock",
                model_name="mock-model",
                vector_dimensions=4,
                top_k=query.top_k,
                result_count=1,
            ),
        )

    def build_context(self, normalized_text: str, tool_gateway, limit: int = 2):
        raise AssertionError("grounded retrieval should not use preview context")


def test_planner_payload_uses_real_retrieval_context_when_available() -> None:
    retrieval_service = GroundedRetrievalService()
    agent_service = AgentService(retrieval_service=retrieval_service)

    payload = agent_service.build_langchain_planner_payload(
        normalized_role="analyst",
        normalized_text="Search policy evidence.",
        registry=build_default_registry(),
    )

    assert retrieval_service.received_query == RetrievalQuery(
        text="Search policy evidence.",
        top_k=2,
    )
    assert payload["retrieval_context"]["retrieval_source"] == "postgresql_pgvector"
    assert "data/trading.md" in payload["planner_prompt"]
    assert "score=0.91" in payload["planner_prompt"]
