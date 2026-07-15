from backend.retrieval.embedding_provider import (
    EmbeddingProvider,
    LocalSentenceTransformerEmbeddingProvider,
    MockEmbeddingProvider,
)
from backend.retrieval.ingestion_models import EmbeddingConfig
from backend.retrieval.service import RetrievalService
from backend.storage.repositories.knowledge_search import KnowledgeSearchRepository
from backend.storage.settings import Settings


def build_embedding_config(settings: Settings) -> EmbeddingConfig:
    return EmbeddingConfig(
        provider=settings.embedding_provider,
        model_name=settings.embedding_model_name,
        vector_dimensions=settings.embedding_dimensions,
        query_prefix=settings.embedding_query_prefix,
    )


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "mock":
        return MockEmbeddingProvider()

    if settings.embedding_provider == "local_sentence_transformer":
        return LocalSentenceTransformerEmbeddingProvider(
            model_name=settings.embedding_model_name,
            device=settings.embedding_device,
            normalize_embeddings=settings.embedding_normalize,
            local_files_only=settings.embedding_local_files_only,
        )

    raise ValueError(
        f"Unsupported embedding provider: {settings.embedding_provider}"
    )


def build_retrieval_service(
    settings: Settings,
    knowledge_search_repository: KnowledgeSearchRepository,
) -> RetrievalService:
    """Build the retrieval orchestrator with one shared runtime configuration."""

    embedding_config = build_embedding_config(settings)
    if not settings.retrieval_enabled:
        return RetrievalService(
            embedding_config=embedding_config,
            enabled=False,
        )

    try:
        embedding_provider = build_embedding_provider(settings)
    except Exception as exc:
        return RetrievalService(
            embedding_config=embedding_config,
            enabled=True,
            runtime_error=type(exc).__name__,
        )

    return RetrievalService(
        embedding_config=embedding_config,
        embedding_provider=embedding_provider,
        knowledge_search_repository=knowledge_search_repository,
        minimum_similarity=settings.retrieval_min_similarity,
    )
