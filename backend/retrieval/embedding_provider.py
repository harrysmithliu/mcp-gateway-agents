from dataclasses import dataclass

from backend.retrieval.ingestion_models import EmbeddingRequest, EmbeddingResponse


class EmbeddingProvider:
    """Defines the minimal interface for an embedding provider."""

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        raise NotImplementedError


@dataclass(slots=True)
class MockEmbeddingProvider(EmbeddingProvider):
    """Provides deterministic local embeddings for ingestion pipeline scaffolding."""

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        vectors = [
            build_mock_embedding_vector(
                text=text,
                vector_dimensions=request.config.vector_dimensions,
            )
            for text in request.texts
        ]

        return EmbeddingResponse(
            vectors=vectors,
            model_name=request.config.model_name,
        )


def build_mock_embedding_vector(
    text: str,
    vector_dimensions: int,
) -> list[float]:
    """Builds a deterministic mock embedding vector for one text input."""

    if vector_dimensions <= 0:
        raise ValueError("vector_dimensions must be positive")

    seed_values = [
        float(len(text)),
        float(len(text.split())),
        float(sum(ord(character) for character in text) % 1000) / 1000.0,
    ]

    repeated_values = (
        seed_values
        * ((vector_dimensions + len(seed_values) - 1) // len(seed_values))
    )

    return repeated_values[:vector_dimensions]