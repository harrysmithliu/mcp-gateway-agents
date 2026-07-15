from dataclasses import dataclass
from typing import Callable

from backend.retrieval.ingestion_loader import (
    DEFAULT_EMBEDDING_CONFIG,
    build_default_ingestion_batch_result,
    build_default_ingestion_batch_result_with_runtime,
)
from backend.retrieval.ingestion_models import IngestionBatchResult
from backend.storage.settings import Settings
from backend.storage.db import DatabaseClient, SQLStatement
from backend.storage.models import (
    ChunkEmbeddingRecord,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    KnowledgeIngestionSourceRecord,
)
from backend.storage.repositories.chunk_embeddings import ChunkEmbeddingRepository
from backend.storage.repositories.knowledge_chunks import KnowledgeChunkRepository
from backend.storage.repositories.knowledge_documents import KnowledgeDocumentRepository
from backend.storage.repositories.base import StatementExecutor
from backend.storage.runtime import StorageBundle


@dataclass(frozen=True, slots=True)
class RetrievalPersistenceResult:
    document_count: int
    chunk_count: int
    embedding_count: int
    statements: tuple[SQLStatement, ...]
    removed_document_count: int = 0


@dataclass(frozen=True, slots=True)
class RetrievalPersistenceRunResult:
    batch_result: IngestionBatchResult
    persistence_result: RetrievalPersistenceResult


@dataclass(slots=True)
class RetrievalPersistenceService:
    knowledge_document_repository: KnowledgeDocumentRepository
    knowledge_chunk_repository: KnowledgeChunkRepository
    chunk_embedding_repository: ChunkEmbeddingRepository

    def build_document_records(
        self,
        batch_result: IngestionBatchResult,
        source_records: tuple[KnowledgeIngestionSourceRecord, ...] = (),
    ) -> list[KnowledgeDocumentRecord]:
        source_records_by_id = {
            record.source_id: record for record in source_records
        }
        records_by_document_id: dict[str, KnowledgeDocumentRecord] = {}
        for chunk_record in batch_result.chunk_records:
            if chunk_record.source_id in records_by_document_id:
                continue
            records_by_document_id[chunk_record.source_id] = KnowledgeDocumentRecord(
                document_id=chunk_record.source_id,
                title=chunk_record.title,
                content_type=str(chunk_record.metadata.get("content_type", "text/plain")),
                access_level=str(chunk_record.metadata.get("access_level", "internal")),
                jurisdiction=(
                    str(chunk_record.metadata["jurisdiction"])
                    if chunk_record.metadata.get("jurisdiction") is not None
                    else None
                ),
                file_path=str(chunk_record.metadata.get("file_path", "")),
                tags=list(chunk_record.metadata.get("tags", [])),
                content_checksum_sha256=(
                    source_records_by_id[chunk_record.source_id].checksum_sha256
                    if chunk_record.source_id in source_records_by_id
                    else None
                ),
                index_fingerprint=(
                    source_records_by_id[chunk_record.source_id].index_fingerprint
                    if chunk_record.source_id in source_records_by_id
                    else None
                ),
            )
        for source_record in source_records:
            if source_record.source_id in records_by_document_id:
                continue
            records_by_document_id[source_record.source_id] = KnowledgeDocumentRecord(
                document_id=source_record.source_id,
                title=source_record.title,
                content_type=source_record.content_type,
                access_level=source_record.access_level,
                jurisdiction=source_record.jurisdiction,
                file_path=source_record.source_path,
                tags=list(source_record.tags),
                content_checksum_sha256=source_record.checksum_sha256,
                index_fingerprint=source_record.index_fingerprint,
            )
        return list(records_by_document_id.values())

    def build_chunk_records(
        self,
        batch_result: IngestionBatchResult,
    ) -> list[KnowledgeChunkRecord]:
        return [
            KnowledgeChunkRecord(
                chunk_id=chunk_record.chunk_id,
                document_id=chunk_record.source_id,
                chunk_index=chunk_record.chunk_index,
                chunk_text=chunk_record.text,
                chunk_metadata=dict(chunk_record.metadata),
            )
            for chunk_record in batch_result.chunk_records
        ]

    def build_embedding_records(
        self,
        batch_result: IngestionBatchResult,
        embedding_provider: str,
    ) -> list[ChunkEmbeddingRecord]:
        return [
            ChunkEmbeddingRecord(
                chunk_id=vector_record.chunk_id,
                embedding_model_name=batch_result.embedding_model_name,
                embedding_provider=embedding_provider,
                vector_dimensions=len(vector_record.embedding),
                embedding=list(vector_record.embedding),
            )
            for vector_record in batch_result.vector_records
        ]

    def persist_batch(
        self,
        batch_result: IngestionBatchResult,
        embedding_provider: str,
    ) -> RetrievalPersistenceResult:
        document_records = self.build_document_records(batch_result)
        chunk_records = self.build_chunk_records(batch_result)
        embedding_records = self.build_embedding_records(
            batch_result=batch_result,
            embedding_provider=embedding_provider,
        )

        statements: list[SQLStatement] = []
        for document_record in document_records:
            statements.append(
                self.knowledge_document_repository.create_document(document_record)
            )
        for chunk_record in chunk_records:
            statements.append(
                self.knowledge_chunk_repository.create_chunk(chunk_record)
            )
        for embedding_record in embedding_records:
            statements.append(
                self.chunk_embedding_repository.create_embedding(embedding_record)
            )

        return RetrievalPersistenceResult(
            document_count=len(document_records),
            chunk_count=len(chunk_records),
            embedding_count=len(embedding_records),
            statements=tuple(statements),
        )

    def persist_refresh_batch_in_transaction(
        self,
        batch_result: IngestionBatchResult,
        embedding_provider: str,
        source_ids_to_reindex: tuple[str, ...],
        removed_source_ids: tuple[str, ...],
        source_records: tuple[KnowledgeIngestionSourceRecord, ...],
        database_client: DatabaseClient,
    ) -> RetrievalPersistenceResult:
        """Synchronizes affected sources atomically and removes stale sources."""

        with database_client.transaction() as transaction:
            bound_service = self._with_executor(transaction)
            return bound_service._persist_refresh_batch(
                batch_result=batch_result,
                embedding_provider=embedding_provider,
                source_ids_to_reindex=source_ids_to_reindex,
                removed_source_ids=removed_source_ids,
                source_records=source_records,
            )

    def _with_executor(self, executor: StatementExecutor) -> "RetrievalPersistenceService":
        return RetrievalPersistenceService(
            knowledge_document_repository=KnowledgeDocumentRepository(executor),
            knowledge_chunk_repository=KnowledgeChunkRepository(executor),
            chunk_embedding_repository=ChunkEmbeddingRepository(executor),
        )

    def _persist_refresh_batch(
        self,
        batch_result: IngestionBatchResult,
        embedding_provider: str,
        source_ids_to_reindex: tuple[str, ...],
        removed_source_ids: tuple[str, ...],
        source_records: tuple[KnowledgeIngestionSourceRecord, ...],
    ) -> RetrievalPersistenceResult:
        document_records = self.build_document_records(
            batch_result,
            source_records=source_records,
        )
        chunk_records = self.build_chunk_records(batch_result)
        embedding_records = self.build_embedding_records(
            batch_result=batch_result,
            embedding_provider=embedding_provider,
        )
        records_by_document_id = {
            record.document_id: record for record in document_records
        }
        chunks_by_document_id: dict[str, list[KnowledgeChunkRecord]] = {}
        for record in chunk_records:
            chunks_by_document_id.setdefault(record.document_id, []).append(record)
        embeddings_by_chunk_id = {
            record.chunk_id: record for record in embedding_records
        }

        statements: list[SQLStatement] = []
        for source_id in removed_source_ids:
            statements.append(self.knowledge_document_repository.delete_document(source_id))

        for source_id in source_ids_to_reindex:
            document_record = records_by_document_id.get(source_id)
            if document_record is None:
                continue
            statements.append(
                self.knowledge_document_repository.create_document(document_record)
            )
            statements.append(
                self.knowledge_chunk_repository.delete_chunks_for_document(source_id)
            )
            for chunk_record in chunks_by_document_id.get(source_id, []):
                statements.append(self.knowledge_chunk_repository.create_chunk(chunk_record))
                embedding_record = embeddings_by_chunk_id.get(chunk_record.chunk_id)
                if embedding_record is not None:
                    statements.append(
                        self.chunk_embedding_repository.create_embedding(embedding_record)
                    )

        return RetrievalPersistenceResult(
            document_count=len(
                [source_id for source_id in source_ids_to_reindex if source_id in records_by_document_id]
            ),
            chunk_count=len(chunk_records),
            embedding_count=len(embedding_records),
            statements=tuple(statements),
            removed_document_count=len(removed_source_ids),
        )


def build_retrieval_persistence_service(
    storage_bundle: StorageBundle,
) -> RetrievalPersistenceService:
    return RetrievalPersistenceService(
        knowledge_document_repository=storage_bundle.knowledge_document_repository,
        knowledge_chunk_repository=storage_bundle.knowledge_chunk_repository,
        chunk_embedding_repository=storage_bundle.chunk_embedding_repository,
    )


def run_default_retrieval_persistence(
    service: RetrievalPersistenceService,
    batch_result_builder: Callable[[], IngestionBatchResult] | None = None,
    embedding_provider: str = DEFAULT_EMBEDDING_CONFIG.provider,
    source_documents: tuple | None = None,
) -> RetrievalPersistenceRunResult:
    if batch_result_builder is None:
        if source_documents is None:
            batch_result_builder = lambda: build_default_ingestion_batch_result()
        else:
            batch_result_builder = lambda: build_default_ingestion_batch_result(
                documents=source_documents
            )
    batch_result = batch_result_builder()
    persistence_result = service.persist_batch(
        batch_result=batch_result,
        embedding_provider=embedding_provider,
    )
    return RetrievalPersistenceRunResult(
        batch_result=batch_result,
        persistence_result=persistence_result,
    )


def run_default_retrieval_persistence_with_runtime(
    service: RetrievalPersistenceService,
    settings: Settings,
    source_documents: tuple | None = None,
) -> RetrievalPersistenceRunResult:
    if source_documents is None:
        batch_result_builder = lambda: build_default_ingestion_batch_result_with_runtime(
            settings
        )
    else:
        batch_result_builder = lambda: build_default_ingestion_batch_result_with_runtime(
            settings,
            documents=source_documents,
        )
    return run_default_retrieval_persistence(
        service=service,
        batch_result_builder=batch_result_builder,
        embedding_provider=settings.embedding_provider,
    )


def run_default_retrieval_refresh_with_runtime(
    service: RetrievalPersistenceService,
    settings: Settings,
    source_documents: tuple,
    source_records: tuple[KnowledgeIngestionSourceRecord, ...],
    source_ids_to_reindex: tuple[str, ...],
    removed_source_ids: tuple[str, ...],
    database_client: DatabaseClient,
) -> RetrievalPersistenceRunResult:
    batch_result = build_default_ingestion_batch_result_with_runtime(
        settings,
        documents=source_documents,
    )
    persistence_result = service.persist_refresh_batch_in_transaction(
        batch_result=batch_result,
        embedding_provider=settings.embedding_provider,
        source_ids_to_reindex=source_ids_to_reindex,
        removed_source_ids=removed_source_ids,
        source_records=source_records,
        database_client=database_client,
    )
    return RetrievalPersistenceRunResult(
        batch_result=batch_result,
        persistence_result=persistence_result,
    )
