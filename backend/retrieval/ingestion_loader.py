from pathlib import Path

from backend.retrieval.embedding_provider import EmbeddingProvider, MockEmbeddingProvider
from backend.retrieval.ingestion_manifest import DEFAULT_INGESTION_DOCUMENTS
from backend.retrieval.ingestion_models import (
    ChunkingConfig,
    EmbeddingConfig,
    EmbeddingRequest,
    EmbeddingResponse,
    IngestionBatchResult,
    IngestionChunkRecord,
    KnowledgeSourceDocument,
    VectorDocumentRecord,
)
from backend.retrieval.runtime import build_embedding_config, build_embedding_provider
from backend.storage.settings import Settings


def load_source_text(document: KnowledgeSourceDocument) -> str:
    """Loads the raw text content for a knowledge source document."""

    return Path(document.file_path).read_text(encoding="utf-8")


def chunk_text(
    text: str,
    chunking_config: ChunkingConfig,
) -> list[str]:
    """Splits source text into ingestion chunks using the current chunking rules."""

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        if not current_chunk:
            current_chunk = paragraph
            continue

        candidate_chunk = current_chunk + "\n\n" + paragraph
        if len(candidate_chunk) <= chunking_config.chunk_size:
            current_chunk = candidate_chunk
            continue

        chunks.append(current_chunk)
        current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def build_ingestion_chunks(
    document: KnowledgeSourceDocument,
    chunking_config: ChunkingConfig,
) -> list[IngestionChunkRecord]:
    """Builds standard ingestion chunk records from one source document."""

    source_text = load_source_text(document)
    chunk_texts = chunk_text(source_text, chunking_config)

    return [
        IngestionChunkRecord(
            chunk_id=f"{document.source_id}-chunk-{index}",
            source_id=document.source_id,
            title=document.title,
            chunk_index=index,
            text=chunk_text_value,
            metadata={
                "content_type": document.content_type,
                "tags": list(document.tags),
                "jurisdiction": document.jurisdiction,
                "access_level": document.access_level,
                "file_path": document.file_path,
            },
        )
        for index, chunk_text_value in enumerate(chunk_texts)
    ]


DEFAULT_CHUNKING_CONFIG = ChunkingConfig(
    chunk_size=500,
    chunk_overlap=50,
)


def build_default_ingestion_chunks(
    documents: tuple[KnowledgeSourceDocument, ...] = DEFAULT_INGESTION_DOCUMENTS,
) -> list[IngestionChunkRecord]:
    """Builds ingestion chunk records for the default ingestion document set."""

    chunk_records: list[IngestionChunkRecord] = []

    for document in documents:
        chunk_records.extend(
            build_ingestion_chunks(
                document=document,
                chunking_config=DEFAULT_CHUNKING_CONFIG,
            )
        )

    return chunk_records


def build_vector_document_record(
    chunk_record: IngestionChunkRecord,
    embedding: list[float],
) -> VectorDocumentRecord:
    """Builds a vector-ready document record from one chunk record and its embedding."""

    return VectorDocumentRecord(
        chunk_id=chunk_record.chunk_id,
        source_id=chunk_record.source_id,
        title=chunk_record.title,
        text=chunk_record.text,
        embedding=embedding,
        metadata=dict(chunk_record.metadata),
    )


def build_vector_document_records(
    chunk_records: list[IngestionChunkRecord],
    embeddings: list[list[float]],
) -> list[VectorDocumentRecord]:
    """Builds vector-ready document records from chunk records and parallel embeddings."""

    if len(chunk_records) != len(embeddings):
        raise ValueError("chunk_records and embeddings must have the same length")

    return [
        build_vector_document_record(
            chunk_record=chunk_record,
            embedding=embedding,
        )
        for chunk_record, embedding in zip(chunk_records, embeddings)
    ]


def build_embedding_request(
    chunk_records: list[IngestionChunkRecord],
    embedding_config: EmbeddingConfig,
) -> EmbeddingRequest:
    """Builds a batch embedding request from ingestion chunk records."""

    return EmbeddingRequest(
        texts=[chunk_record.text for chunk_record in chunk_records],
        config=embedding_config,
    )


def build_vector_documents_from_embedding_response(
    chunk_records: list[IngestionChunkRecord],
    embedding_response: EmbeddingResponse,
) -> list[VectorDocumentRecord]:
    """Builds vector-ready document records from chunk records and one embedding response."""

    return build_vector_document_records(
        chunk_records=chunk_records,
        embeddings=embedding_response.vectors,
    )


def build_vector_documents_with_provider(
    chunk_records: list[IngestionChunkRecord],
    embedding_config: EmbeddingConfig,
    embedding_provider: EmbeddingProvider,
) -> list[VectorDocumentRecord]:
    """Builds vector-ready document records by running one embedding provider call."""

    embedding_request = build_embedding_request(
        chunk_records=chunk_records,
        embedding_config=embedding_config,
    )

    embedding_response = embedding_provider.embed(embedding_request)

    return build_vector_documents_from_embedding_response(
        chunk_records=chunk_records,
        embedding_response=embedding_response,
    )


DEFAULT_EMBEDDING_CONFIG = EmbeddingConfig(
    provider="mock",
    model_name="mock-embedding-model",
    vector_dimensions=4,
)


def build_default_vector_documents(
    documents: tuple[KnowledgeSourceDocument, ...] = DEFAULT_INGESTION_DOCUMENTS,
) -> list[VectorDocumentRecord]:
    """Builds vector-ready documents for the default ingestion document set."""

    chunk_records = (
        build_default_ingestion_chunks()
        if documents is DEFAULT_INGESTION_DOCUMENTS
        else build_default_ingestion_chunks(documents=documents)
    )

    return build_vector_documents_with_provider(
        chunk_records=chunk_records,
        embedding_config=DEFAULT_EMBEDDING_CONFIG,
        embedding_provider=MockEmbeddingProvider(),
    )


def build_default_ingestion_batch_result(
    documents: tuple[KnowledgeSourceDocument, ...] = DEFAULT_INGESTION_DOCUMENTS,
) -> IngestionBatchResult:
    """Builds the default in-memory ingestion batch result."""

    chunk_records = (
        build_default_ingestion_chunks()
        if documents is DEFAULT_INGESTION_DOCUMENTS
        else build_default_ingestion_chunks(documents=documents)
    )
    if not chunk_records:
        return IngestionBatchResult(
            chunk_records=[],
            vector_records=[],
            embedding_model_name=DEFAULT_EMBEDDING_CONFIG.model_name,
            chunk_count=0,
            vector_count=0,
        )
    vector_records = build_vector_documents_with_provider(
        chunk_records=chunk_records,
        embedding_config=DEFAULT_EMBEDDING_CONFIG,
        embedding_provider=MockEmbeddingProvider(),
    )

    return IngestionBatchResult(
        chunk_records=chunk_records,
        vector_records=vector_records,
        embedding_model_name=DEFAULT_EMBEDDING_CONFIG.model_name,
        chunk_count=len(chunk_records),
        vector_count=len(vector_records),
    )


def build_default_vector_documents_with_runtime(
    settings: Settings,
    documents: tuple[KnowledgeSourceDocument, ...] = DEFAULT_INGESTION_DOCUMENTS,
) -> list[VectorDocumentRecord]:
    """Builds vector-ready documents using the configured runtime embedding provider."""

    chunk_records = (
        build_default_ingestion_chunks()
        if documents is DEFAULT_INGESTION_DOCUMENTS
        else build_default_ingestion_chunks(documents=documents)
    )
    if not chunk_records:
        return []

    return build_vector_documents_with_provider(
        chunk_records=chunk_records,
        embedding_config=build_embedding_config(settings),
        embedding_provider=build_embedding_provider(settings),
    )


def build_default_ingestion_batch_result_with_runtime(
    settings: Settings,
    documents: tuple[KnowledgeSourceDocument, ...] = DEFAULT_INGESTION_DOCUMENTS,
) -> IngestionBatchResult:
    """Builds the default ingestion batch result with the configured runtime provider."""

    chunk_records = (
        build_default_ingestion_chunks()
        if documents is DEFAULT_INGESTION_DOCUMENTS
        else build_default_ingestion_chunks(documents=documents)
    )
    if not chunk_records:
        embedding_config = build_embedding_config(settings)
        return IngestionBatchResult(
            chunk_records=[],
            vector_records=[],
            embedding_model_name=embedding_config.model_name,
            chunk_count=0,
            vector_count=0,
        )
    embedding_config = build_embedding_config(settings)
    vector_records = build_vector_documents_with_provider(
        chunk_records=chunk_records,
        embedding_config=embedding_config,
        embedding_provider=build_embedding_provider(settings),
    )

    return IngestionBatchResult(
        chunk_records=chunk_records,
        vector_records=vector_records,
        embedding_model_name=embedding_config.model_name,
        chunk_count=len(chunk_records),
        vector_count=len(vector_records),
    )
