from backend.retrieval.contracts import QueryEmbedding, RetrievalQuery
from backend.retrieval.embedding_provider import EmbeddingProvider
from backend.retrieval.ingestion_models import EmbeddingConfig, EmbeddingRequest


def build_query_embedding_request(
    query: RetrievalQuery,
    embedding_config: EmbeddingConfig,
) -> EmbeddingRequest:
    """Build one provider request while applying the configured query prefix."""

    query_text = f"{embedding_config.query_prefix}{query.text}"
    return EmbeddingRequest(
        texts=[query_text],
        config=embedding_config,
    )


def embed_query(
    query: RetrievalQuery,
    embedding_config: EmbeddingConfig,
    embedding_provider: EmbeddingProvider,
) -> QueryEmbedding:
    """Embed one retrieval query and enforce the configured vector contract."""

    response = embedding_provider.embed(
        build_query_embedding_request(
            query=query,
            embedding_config=embedding_config,
        )
    )
    if len(response.vectors) != 1:
        raise ValueError("query embedding provider must return exactly one vector")

    vector = [float(value) for value in response.vectors[0]]
    if len(vector) != embedding_config.vector_dimensions:
        raise ValueError(
            "query embedding dimensions do not match the configured vector dimensions"
        )

    return QueryEmbedding(
        vector=vector,
        provider=embedding_config.provider,
        model_name=response.model_name,
        vector_dimensions=len(vector),
    )
