from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.agent.ports import ToolGatewayPort


@dataclass(frozen=True, slots=True)
class RetrievalChunk:
    document_id: str
    title: str
    summary: str
    matched_terms: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RetrievalCitation:
    document_id: str
    title: str


@dataclass(frozen=True, slots=True)
class RetrievalContext:
    rag_enabled: bool
    retrieval_source: str
    retrieved_chunks: list[RetrievalChunk] = field(default_factory=list)
    citations: list[RetrievalCitation] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "rag_enabled": self.rag_enabled,
            "retrieval_source": self.retrieval_source,
            "retrieved_chunks": [asdict(chunk) for chunk in self.retrieved_chunks],
            "citations": [asdict(citation) for citation in self.citations],
        }


@dataclass(slots=True)
class RetrievalService:
    """Placeholder for document chunking and vector retrieval."""

    vector_backend: str = "postgresql-pgvector"

    def describe(self) -> str:
        return (
            "Placeholder retrieval service. "
            "Chunking, embedding persistence, and vector search will be added in later batches."
        )

    def build_context(
        self,
        normalized_text: str,
        tool_gateway: "ToolGatewayPort",
        limit: int = 2,
    ) -> RetrievalContext:
        matched_records = tool_gateway.preview_knowledge_matches(
            query_text=normalized_text,
            limit=limit,
        )
        if not matched_records:
            return RetrievalContext(
                rag_enabled=False,
                retrieval_source="knowledge_preview",
            )

        return RetrievalContext(
            rag_enabled=True,
            retrieval_source="knowledge_preview",
            retrieved_chunks=[
                RetrievalChunk(
                    document_id=match["document_id"],
                    title=match["title"],
                    summary=match["summary"],
                    matched_terms=list(match["matched_terms"]),
                )
                for match in matched_records
            ],
            citations=[
                RetrievalCitation(
                    document_id=match["document_id"],
                    title=match["title"],
                )
                for match in matched_records
            ],
        )
