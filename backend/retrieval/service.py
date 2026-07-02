from dataclasses import dataclass


@dataclass(slots=True)
class RetrievalService:
    """Placeholder for document chunking and vector retrieval."""

    vector_backend: str = "postgresql-pgvector"

    def describe(self) -> str:
        return (
            "Placeholder retrieval service. "
            "Chunking, embedding persistence, and vector search will be added in later batches."
        )
