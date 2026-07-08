import pytest

from backend.retrieval.embedding_provider import (
    MockEmbeddingProvider,
    build_mock_embedding_vector,
)
from backend.retrieval.ingestion_models import EmbeddingConfig, EmbeddingRequest


def test_build_mock_embedding_vector_returns_requested_dimensions() -> None:
    vector = build_mock_embedding_vector(
        text="Suspicious trade alert requires escalation.",
        vector_dimensions=5,
    )

    assert len(vector) == 5
    assert all(isinstance(value, float) for value in vector)


def test_build_mock_embedding_vector_raises_on_non_positive_dimensions() -> None:
    with pytest.raises(ValueError, match="positive"):
        build_mock_embedding_vector(
            text="Test text",
            vector_dimensions=0,
        )


def test_mock_embedding_provider_returns_vectors_for_all_texts() -> None:
    provider = MockEmbeddingProvider()

    response = provider.embed(
        EmbeddingRequest(
            texts=[
                "First chunk text.",
                "Second chunk text.",
            ],
            config=EmbeddingConfig(
                provider="mock",
                model_name="mock-embedding-model",
                vector_dimensions=4,
            ),
        )
    )

    assert response.model_name == "mock-embedding-model"
    assert len(response.vectors) == 2
    assert all(len(vector) == 4 for vector in response.vectors)