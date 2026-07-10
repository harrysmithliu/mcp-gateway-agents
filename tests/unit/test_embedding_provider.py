import pytest

from backend.retrieval.embedding_provider import (
    LocalSentenceTransformerEmbeddingProvider,
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


def test_local_sentence_transformer_embedding_provider_embeds_texts() -> None:
    captured_calls: list[dict[str, object]] = []

    class FakeSentenceTransformer:
        def __init__(self, model_name: str, device: str) -> None:
            captured_calls.append(
                {
                    "event": "init",
                    "model_name": model_name,
                    "device": device,
                }
            )

        def encode(
            self,
            texts: list[str],
            normalize_embeddings: bool,
        ) -> list[list[float]]:
            captured_calls.append(
                {
                    "event": "encode",
                    "texts": list(texts),
                    "normalize_embeddings": normalize_embeddings,
                }
            )
            return [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    provider = LocalSentenceTransformerEmbeddingProvider(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device="cpu",
        normalize_embeddings=True,
        sentence_transformer_factory=FakeSentenceTransformer,
    )

    response = provider.embed(
        EmbeddingRequest(
            texts=["First chunk text.", "Second chunk text."],
            config=EmbeddingConfig(
                provider="local_sentence_transformer",
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                vector_dimensions=384,
            ),
        )
    )

    assert response.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert response.vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert captured_calls == [
        {
            "event": "init",
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "device": "cpu",
        },
        {
            "event": "encode",
            "texts": ["First chunk text.", "Second chunk text."],
            "normalize_embeddings": True,
        },
    ]


def test_local_sentence_transformer_embedding_provider_raises_without_dependency() -> None:
    provider = LocalSentenceTransformerEmbeddingProvider(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        sentence_transformer_factory=lambda *args, **kwargs: (_ for _ in ()).throw(
            ImportError("missing dependency")
        ),
    )

    with pytest.raises(RuntimeError, match="sentence-transformers"):
        provider.embed(
            EmbeddingRequest(
                texts=["Test text"],
                config=EmbeddingConfig(
                    provider="local_sentence_transformer",
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    vector_dimensions=384,
                ),
            )
        )
