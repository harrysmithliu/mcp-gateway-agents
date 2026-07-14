from backend.retrieval.contracts import QueryEmbedding, RetrievalQuery
from backend.retrieval.embedding_provider import EmbeddingProvider
from backend.retrieval.ingestion_models import (
    EmbeddingConfig,
    EmbeddingRequest,
    EmbeddingResponse,
)
from backend.retrieval.service import RetrievalService
from backend.storage.models import KnowledgeSearchRecord


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        assert request.texts == ["policy evidence"]
        return EmbeddingResponse(
            vectors=[[0.1, 0.2, 0.3, 0.4]],
            model_name=request.config.model_name,
        )


class FailingEmbeddingProvider(EmbeddingProvider):
    def embed(self, _request: EmbeddingRequest) -> EmbeddingResponse:
        raise ConnectionError("database or model unavailable")


class FakeKnowledgeSearchRepository:
    def __init__(self, records: list[KnowledgeSearchRecord]) -> None:
        self.records = records
        self.received_query: RetrievalQuery | None = None
        self.received_embedding: QueryEmbedding | None = None

    def search_similar_chunks(
        self,
        query: RetrievalQuery,
        query_embedding: QueryEmbedding,
    ) -> list[KnowledgeSearchRecord]:
        self.received_query = query
        self.received_embedding = query_embedding
        return self.records


def build_service(repository: FakeKnowledgeSearchRepository) -> RetrievalService:
    return RetrievalService(
        embedding_config=EmbeddingConfig(
            provider="fake",
            model_name="fake-embedding-model",
            vector_dimensions=4,
        ),
        embedding_provider=FakeEmbeddingProvider(),
        knowledge_search_repository=repository,
    )


def test_retrieval_service_maps_vector_rows_to_chunks_and_citations() -> None:
    repository = FakeKnowledgeSearchRepository(
        records=[
            KnowledgeSearchRecord(
                chunk_id="chunk-1",
                document_id="doc-1",
                title="Trading Policy",
                source_path="data/trading.md",
                chunk_index=2,
                chunk_text="Escalate suspicious activity.",
                chunk_metadata={"topic": "surveillance"},
                similarity_score=0.91,
            )
        ]
    )
    service = build_service(repository)

    result = service.retrieve(
        RetrievalQuery(
            text="policy evidence",
            top_k=3,
            access_level="internal",
        )
    )

    assert repository.received_query is not None
    assert repository.received_query.text == "policy evidence"
    assert repository.received_embedding is not None
    assert repository.received_embedding.vector_dimensions == 4
    assert result.rag_enabled is True
    assert result.retrieval_source == "postgresql_pgvector"
    assert result.retrieved_chunks[0].chunk_id == "chunk-1"
    assert result.retrieved_chunks[0].score == 0.91
    assert result.citations[0].source_path == "data/trading.md"
    assert result.citations[0].excerpt == "Escalate suspicious activity."
    assert result.metadata.result_count == 1
    assert result.metadata.filters == {"access_level": "internal"}


def test_retrieval_service_returns_disabled_empty_result_without_matches() -> None:
    service = build_service(FakeKnowledgeSearchRepository(records=[]))

    result = service.retrieve(RetrievalQuery(text="policy evidence"))

    assert result.rag_enabled is False
    assert result.retrieved_chunks == []
    assert result.citations == []
    assert result.metadata.result_count == 0
    assert result.metadata.status == "empty"


def test_retrieval_service_returns_disabled_result_when_runtime_is_disabled() -> None:
    service = RetrievalService(
        embedding_config=EmbeddingConfig(
            provider="local_sentence_transformer",
            model_name="disabled-model",
            vector_dimensions=384,
        ),
        enabled=False,
    )

    result = service.retrieve(RetrievalQuery(text="policy evidence"))

    assert result.rag_enabled is False
    assert result.retrieved_chunks == []
    assert result.metadata.status == "disabled"
    assert result.metadata.failure_reason == "disabled_by_configuration"


def test_retrieval_service_returns_unavailable_result_for_runtime_configuration_error() -> None:
    service = RetrievalService(
        embedding_config=EmbeddingConfig(
            provider="unknown",
            model_name="invalid-model",
            vector_dimensions=4,
        ),
        runtime_error="ValueError",
    )

    result = service.retrieve(RetrievalQuery(text="policy evidence"))

    assert result.rag_enabled is False
    assert result.metadata.status == "unavailable"
    assert result.metadata.failure_reason == "ValueError"
    assert result.metadata.latency_ms >= 0


def test_retrieval_service_returns_safe_failure_metadata_on_runtime_error() -> None:
    service = RetrievalService(
        embedding_config=EmbeddingConfig(
            provider="fake",
            model_name="fake-embedding-model",
            vector_dimensions=4,
        ),
        embedding_provider=FailingEmbeddingProvider(),
        knowledge_search_repository=FakeKnowledgeSearchRepository(records=[]),
    )

    result = service.retrieve(RetrievalQuery(text="policy evidence"))

    assert result.rag_enabled is False
    assert result.retrieved_chunks == []
    assert result.citations == []
    assert result.metadata.status == "failed"
    assert result.metadata.failure_reason == "ConnectionError"
    assert result.metadata.latency_ms >= 0


def test_retrieval_service_requires_runtime_wiring_for_vector_search() -> None:
    service = RetrievalService()

    try:
        service.retrieve(RetrievalQuery(text="policy evidence"))
    except RuntimeError as exc:
        assert "runtime is not configured" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for incomplete retrieval runtime")
