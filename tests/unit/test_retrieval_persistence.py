import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.retrieval.ingestion_models import (
    IngestionBatchResult,
    IngestionChunkRecord,
    VectorDocumentRecord,
)
from backend.retrieval.persistence import (
    RetrievalPersistenceService,
    build_retrieval_persistence_service,
    run_default_retrieval_persistence,
    run_default_retrieval_persistence_with_runtime,
)
from backend.storage.settings import Settings
from backend.storage.db import SQLStatement
from backend.storage.models import (
    ChunkEmbeddingRecord,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    KnowledgeIngestionSourceRecord,
)


class FakeKnowledgeDocumentRepository:
    def __init__(self) -> None:
        self.records: list[KnowledgeDocumentRecord] = []

    def create_document(self, record: KnowledgeDocumentRecord) -> SQLStatement:
        self.records.append(record)
        return SQLStatement(
            sql="INSERT INTO knowledge.knowledge_documents (...)",
            params={"document_id": record.document_id},
        )


class FakeKnowledgeChunkRepository:
    def __init__(self) -> None:
        self.records: list[KnowledgeChunkRecord] = []

    def create_chunk(self, record: KnowledgeChunkRecord) -> SQLStatement:
        self.records.append(record)
        return SQLStatement(
            sql="INSERT INTO knowledge.knowledge_chunks (...)",
            params={"chunk_id": record.chunk_id},
        )


class FakeChunkEmbeddingRepository:
    def __init__(self) -> None:
        self.records: list[ChunkEmbeddingRecord] = []

    def create_embedding(self, record: ChunkEmbeddingRecord) -> SQLStatement:
        self.records.append(record)
        return SQLStatement(
            sql="INSERT INTO knowledge.chunk_embeddings (...)",
            params={"chunk_id": record.chunk_id},
        )


class FakePlannerlessPersistenceService:
    def __init__(self) -> None:
        self.calls: list[tuple[IngestionBatchResult, str]] = []
        self.result = object()

    def persist_batch(
        self,
        batch_result: IngestionBatchResult,
        embedding_provider: str,
    ) -> object:
        self.calls.append((batch_result, embedding_provider))
        return self.result


class FakeDatabaseClient:
    def __init__(self) -> None:
        self.statements: list[SQLStatement] = []

    @contextmanager
    def transaction(self):
        executor = SimpleNamespace(
            execute=lambda statement: self.statements.append(statement),
            fetch_all=lambda _statement: [],
        )
        yield executor


def test_retrieval_persistence_service_persists_batch_result() -> None:
    document_repository = FakeKnowledgeDocumentRepository()
    chunk_repository = FakeKnowledgeChunkRepository()
    embedding_repository = FakeChunkEmbeddingRepository()
    service = RetrievalPersistenceService(
        knowledge_document_repository=document_repository,
        knowledge_chunk_repository=chunk_repository,
        chunk_embedding_repository=embedding_repository,
    )

    batch_result = IngestionBatchResult(
        chunk_records=[
            IngestionChunkRecord(
                chunk_id="kb-policy-trading-surveillance-chunk-0",
                source_id="kb-policy-trading-surveillance",
                title="Trading Surveillance Policy",
                chunk_index=0,
                text="Escalate suspicious trading activity for analyst review.",
                metadata={
                    "content_type": "text/markdown",
                    "tags": ["policy", "trading"],
                    "jurisdiction": "global",
                    "access_level": "internal",
                    "file_path": "/tmp/trading_surveillance_policy.md",
                },
            ),
            IngestionChunkRecord(
                chunk_id="kb-policy-trading-surveillance-chunk-1",
                source_id="kb-policy-trading-surveillance",
                title="Trading Surveillance Policy",
                chunk_index=1,
                text="Document findings and escalate when required.",
                metadata={
                    "content_type": "text/markdown",
                    "tags": ["policy", "trading"],
                    "jurisdiction": "global",
                    "access_level": "internal",
                    "file_path": "/tmp/trading_surveillance_policy.md",
                },
            ),
        ],
        vector_records=[
            VectorDocumentRecord(
                chunk_id="kb-policy-trading-surveillance-chunk-0",
                source_id="kb-policy-trading-surveillance",
                title="Trading Surveillance Policy",
                text="Escalate suspicious trading activity for analyst review.",
                embedding=[0.1, 0.2, 0.3, 0.4],
                metadata={"access_level": "internal"},
            ),
            VectorDocumentRecord(
                chunk_id="kb-policy-trading-surveillance-chunk-1",
                source_id="kb-policy-trading-surveillance",
                title="Trading Surveillance Policy",
                text="Document findings and escalate when required.",
                embedding=[0.5, 0.6, 0.7, 0.8],
                metadata={"access_level": "internal"},
            ),
        ],
        embedding_model_name="mock-embedding-model",
        chunk_count=2,
        vector_count=2,
    )

    result = service.persist_batch(
        batch_result=batch_result,
        embedding_provider="mock",
    )

    assert result.document_count == 1
    assert result.chunk_count == 2
    assert result.embedding_count == 2
    assert len(result.statements) == 5

    assert document_repository.records == [
        KnowledgeDocumentRecord(
            document_id="kb-policy-trading-surveillance",
            title="Trading Surveillance Policy",
            content_type="text/markdown",
            access_level="internal",
            file_path="/tmp/trading_surveillance_policy.md",
            tags=["policy", "trading"],
            jurisdiction="global",
        )
    ]
    assert [record.chunk_id for record in chunk_repository.records] == [
        "kb-policy-trading-surveillance-chunk-0",
        "kb-policy-trading-surveillance-chunk-1",
    ]
    assert [record.chunk_id for record in embedding_repository.records] == [
        "kb-policy-trading-surveillance-chunk-0",
        "kb-policy-trading-surveillance-chunk-1",
    ]
    assert all(record.embedding_provider == "mock" for record in embedding_repository.records)
    assert all(record.embedding_model_name == "mock-embedding-model" for record in embedding_repository.records)


def test_refresh_persistence_rebuilds_selected_sources_and_removes_stale_sources() -> None:
    service = RetrievalPersistenceService(
        knowledge_document_repository=FakeKnowledgeDocumentRepository(),
        knowledge_chunk_repository=FakeKnowledgeChunkRepository(),
        chunk_embedding_repository=FakeChunkEmbeddingRepository(),
    )
    database_client = FakeDatabaseClient()
    batch_result = IngestionBatchResult(
        chunk_records=[
            IngestionChunkRecord(
                chunk_id="source-1-chunk-0",
                source_id="source-1",
                title="Source 1",
                chunk_index=0,
                text="Updated source text",
                metadata={"content_type": "text/markdown", "access_level": "internal"},
            )
        ],
        vector_records=[
            VectorDocumentRecord(
                chunk_id="source-1-chunk-0",
                source_id="source-1",
                title="Source 1",
                text="Updated source text",
                embedding=[0.1, 0.2, 0.3, 0.4],
            )
        ],
        embedding_model_name="mock-model",
        chunk_count=1,
        vector_count=1,
    )
    source_record = KnowledgeIngestionSourceRecord(
        run_id="run-1",
        source_id="source-1",
        title="Source 1",
        source_path="data/source-1.md",
        checksum_sha256="b" * 64,
        byte_size=20,
        content_type="text/markdown",
        access_level="internal",
        index_fingerprint="f" * 64,
    )

    result = service.persist_refresh_batch_in_transaction(
        batch_result=batch_result,
        embedding_provider="mock",
        source_ids_to_reindex=("source-1",),
        removed_source_ids=("removed-source",),
        source_records=(source_record,),
        database_client=database_client,
    )

    assert result.document_count == 1
    assert result.chunk_count == 1
    assert result.embedding_count == 1
    assert result.removed_document_count == 1
    assert "DELETE FROM knowledge.knowledge_documents" in database_client.statements[0].sql
    assert database_client.statements[1].params["content_checksum_sha256"] == "b" * 64
    assert "DELETE FROM knowledge.knowledge_chunks" in database_client.statements[2].sql


def test_build_retrieval_persistence_service_uses_storage_bundle_repositories() -> None:
    document_repository = FakeKnowledgeDocumentRepository()
    chunk_repository = FakeKnowledgeChunkRepository()
    embedding_repository = FakeChunkEmbeddingRepository()

    storage_bundle = SimpleNamespace(
        knowledge_document_repository=document_repository,
        knowledge_chunk_repository=chunk_repository,
        chunk_embedding_repository=embedding_repository,
    )

    service = build_retrieval_persistence_service(storage_bundle)

    assert service.knowledge_document_repository is document_repository
    assert service.knowledge_chunk_repository is chunk_repository
    assert service.chunk_embedding_repository is embedding_repository


def test_run_default_retrieval_persistence_uses_default_batch_and_provider(
    monkeypatch,
) -> None:
    batch_result = IngestionBatchResult(
        chunk_records=[
            IngestionChunkRecord(
                chunk_id="chunk-1",
                source_id="source-1",
                title="Doc 1",
                chunk_index=0,
                text="Chunk text",
                metadata={"access_level": "internal"},
            )
        ],
        vector_records=[
            VectorDocumentRecord(
                chunk_id="chunk-1",
                source_id="source-1",
                title="Doc 1",
                text="Chunk text",
                embedding=[0.1, 0.2, 0.3, 0.4],
                metadata={"access_level": "internal"},
            )
        ],
        embedding_model_name="mock-embedding-model",
        chunk_count=1,
        vector_count=1,
    )
    service = FakePlannerlessPersistenceService()

    monkeypatch.setattr(
        "backend.retrieval.persistence.build_default_ingestion_batch_result",
        lambda: batch_result,
    )

    run_result = run_default_retrieval_persistence(service)

    assert run_result.batch_result is batch_result
    assert run_result.persistence_result is service.result
    assert service.calls == [(batch_result, "mock")]


def test_run_default_retrieval_persistence_with_runtime_uses_settings_driven_builder(
    monkeypatch,
) -> None:
    batch_result = IngestionBatchResult(
        chunk_records=[
            IngestionChunkRecord(
                chunk_id="chunk-1",
                source_id="source-1",
                title="Doc 1",
                chunk_index=0,
                text="Chunk text",
                metadata={"access_level": "internal"},
            )
        ],
        vector_records=[
            VectorDocumentRecord(
                chunk_id="chunk-1",
                source_id="source-1",
                title="Doc 1",
                text="Chunk text",
                embedding=[0.1, 0.2, 0.3],
                metadata={"access_level": "internal"},
            )
        ],
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        chunk_count=1,
        vector_count=1,
    )
    service = FakePlannerlessPersistenceService()
    settings = Settings(
        embedding_provider="local_sentence_transformer",
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dimensions=384,
    )

    monkeypatch.setattr(
        "backend.retrieval.persistence.build_default_ingestion_batch_result_with_runtime",
        lambda runtime_settings: batch_result,
    )

    run_result = run_default_retrieval_persistence_with_runtime(service, settings)

    assert run_result.batch_result is batch_result
    assert run_result.persistence_result is service.result
    assert service.calls == [(batch_result, "local_sentence_transformer")]
