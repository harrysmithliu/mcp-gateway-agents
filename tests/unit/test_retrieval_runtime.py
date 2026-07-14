from backend.retrieval.embedding_provider import (
    LocalSentenceTransformerEmbeddingProvider,
    MockEmbeddingProvider,
)
from backend.retrieval.ingestion_models import EmbeddingConfig
from backend.retrieval.runtime import (
    build_embedding_config,
    build_embedding_provider,
    build_retrieval_service,
)
from backend.storage.repositories.knowledge_search import KnowledgeSearchRepository
from backend.storage.settings import Settings


def test_build_embedding_config_uses_settings_values() -> None:
    settings = Settings(
        embedding_provider="local_sentence_transformer",
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dimensions=384,
    )

    config = build_embedding_config(settings)

    assert config == EmbeddingConfig(
        provider="local_sentence_transformer",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        vector_dimensions=384,
    )


def test_build_embedding_provider_returns_mock_provider() -> None:
    settings = Settings(embedding_provider="mock")

    provider = build_embedding_provider(settings)

    assert isinstance(provider, MockEmbeddingProvider)


def test_build_embedding_provider_returns_local_sentence_transformer_provider() -> None:
    settings = Settings(
        embedding_provider="local_sentence_transformer",
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_device="cpu",
        embedding_normalize=True,
    )

    provider = build_embedding_provider(settings)

    assert isinstance(provider, LocalSentenceTransformerEmbeddingProvider)
    assert provider.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert provider.device == "cpu"
    assert provider.normalize_embeddings is True


def test_build_embedding_provider_raises_on_unknown_provider() -> None:
    settings = Settings(embedding_provider="unknown")

    try:
        build_embedding_provider(settings)
    except ValueError as exc:
        assert "Unsupported embedding provider" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown embedding provider")


def test_build_retrieval_service_wires_embedding_runtime_and_repository() -> None:
    settings = Settings(
        embedding_provider="mock",
        embedding_model_name="mock-embedding-model",
        embedding_dimensions=4,
    )
    repository = KnowledgeSearchRepository(executor=object())

    retrieval_service = build_retrieval_service(settings, repository)

    assert retrieval_service.embedding_config == build_embedding_config(settings)
    assert retrieval_service.embedding_provider is not None
    assert retrieval_service.knowledge_search_repository is repository
    assert retrieval_service.runtime_status().state == "ready"


def test_build_retrieval_service_can_be_disabled_without_building_provider() -> None:
    settings = Settings(
        retrieval_enabled=False,
        embedding_provider="unknown",
        embedding_model_name="disabled-model",
        embedding_dimensions=4,
    )

    retrieval_service = build_retrieval_service(
        settings,
        KnowledgeSearchRepository(executor=object()),
    )

    status = retrieval_service.runtime_status()

    assert status.state == "disabled"
    assert status.enabled is False
    assert status.reason == "disabled_by_configuration"


def test_build_retrieval_service_contains_configuration_failure_without_startup_error() -> None:
    settings = Settings(
        embedding_provider="unknown",
        embedding_model_name="invalid-model",
        embedding_dimensions=4,
    )

    retrieval_service = build_retrieval_service(
        settings,
        KnowledgeSearchRepository(executor=object()),
    )

    status = retrieval_service.runtime_status()

    assert status.state == "unavailable"
    assert status.enabled is True
    assert status.reason == "ValueError"
