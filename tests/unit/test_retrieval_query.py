import pytest

from backend.retrieval.contracts import RetrievalQuery
from backend.retrieval.embedding_provider import MockEmbeddingProvider
from backend.retrieval.ingestion_models import EmbeddingConfig, EmbeddingResponse
from backend.retrieval.query import build_query_embedding_request, embed_query


def test_retrieval_query_normalizes_text_and_validates_top_k() -> None:
    query = RetrievalQuery(text="  policy evidence  ", top_k=3)

    assert query.text == "policy evidence"
    assert query.top_k == 3

    with pytest.raises(ValueError, match="must not be empty"):
        RetrievalQuery(text=" ")
    with pytest.raises(ValueError, match="between 1 and 50"):
        RetrievalQuery(text="policy", top_k=51)


def test_build_query_embedding_request_applies_query_prefix() -> None:
    query = RetrievalQuery(text="policy evidence")
    config = EmbeddingConfig(
        provider="mock",
        model_name="mock-embedding-model",
        vector_dimensions=4,
        query_prefix="query: ",
    )

    request = build_query_embedding_request(query, config)

    assert request.texts == ["query: policy evidence"]
    assert request.config is config


def test_embed_query_returns_one_dimension_checked_query_embedding() -> None:
    query = RetrievalQuery(text="policy evidence")
    config = EmbeddingConfig(
        provider="mock",
        model_name="mock-embedding-model",
        vector_dimensions=4,
    )

    query_embedding = embed_query(
        query=query,
        embedding_config=config,
        embedding_provider=MockEmbeddingProvider(),
    )

    assert len(query_embedding.vector) == 4
    assert query_embedding.provider == "mock"
    assert query_embedding.model_name == "mock-embedding-model"
    assert query_embedding.vector_dimensions == 4


def test_embed_query_rejects_provider_dimension_mismatch() -> None:
    class MismatchedEmbeddingProvider:
        def embed(self, _request):
            return EmbeddingResponse(
                vectors=[[0.1, 0.2, 0.3]],
                model_name="mock-embedding-model",
            )

    query = RetrievalQuery(text="policy evidence")
    config = EmbeddingConfig(
        provider="mock",
        model_name="mock-embedding-model",
        vector_dimensions=4,
    )

    with pytest.raises(ValueError, match="dimensions"):
        embed_query(
            query=query,
            embedding_config=config,
            embedding_provider=MismatchedEmbeddingProvider(),
        )
