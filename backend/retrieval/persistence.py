from dataclasses import dataclass

from backend.retrieval.ingestion_loader import (
    DEFAULT_EMBEDDING_CONFIG,
    build_default_ingestion_batch_result,
)
from backend.retrieval.ingestion_models import IngestionBatchResult
from backend.storage.db import SQLStatement
from backend.storage.models import (
    ChunkEmbeddingRecord,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
)
from backend.storage.repositories.chunk_embeddings import ChunkEmbeddingRepository
from backend.storage.repositories.knowledge_chunks import KnowledgeChunkRepository
from backend.storage.repositories.knowledge_documents import KnowledgeDocumentRepository
from backend.storage.runtime import StorageBundle


@dataclass(frozen=True, slots=True)
class RetrievalPersistenceResult:
    document_count: int
    chunk_count: int
    embedding_count: int
    statements: tuple[SQLStatement, ...]


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
    ) -> list[KnowledgeDocumentRecord]:
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
    embedding_provider: str = DEFAULT_EMBEDDING_CONFIG.provider,
) -> RetrievalPersistenceRunResult:
    batch_result = build_default_ingestion_batch_result()
    persistence_result = service.persist_batch(
        batch_result=batch_result,
        embedding_provider=embedding_provider,
    )
    return RetrievalPersistenceRunResult(
        batch_result=batch_result,
        persistence_result=persistence_result,
    )
