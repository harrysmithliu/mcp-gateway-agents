import pytest

from backend.retrieval.embedding_provider import MockEmbeddingProvider
from backend.retrieval.ingestion_loader import (
    DEFAULT_CHUNKING_CONFIG,
    build_default_ingestion_batch_result,
    build_default_ingestion_chunks,
    build_default_vector_documents,
    build_embedding_request,
    build_vector_document_record,
    build_vector_document_records,
    build_vector_documents_from_embedding_response,
    build_vector_documents_with_provider,
    chunk_text,
)
from backend.retrieval.ingestion_manifest import DEFAULT_INGESTION_DOCUMENTS
from backend.retrieval.ingestion_models import ChunkingConfig, EmbeddingConfig, EmbeddingResponse, IngestionChunkRecord


def test_chunk_text_returns_chunks_for_paragraph_input() -> None:
    text = "\n\n".join(
        [
            "Paragraph one about trade surveillance.",
            "Paragraph two about alert review workflows.",
            "Paragraph three about escalation handling.",
        ]
    )

    chunks = chunk_text(
        text=text,
        chunking_config=DEFAULT_CHUNKING_CONFIG,
    )

    assert len(chunks) >= 1
    assert all(chunk.strip() for chunk in chunks)


def test_chunk_text_splits_when_chunk_size_is_small() -> None:
    text = "\n\n".join(
        [
            "A" * 40,
            "B" * 40,
            "C" * 40,
        ]
    )

    chunks = chunk_text(
        text=text,
        chunking_config=ChunkingConfig(
            chunk_size=50,
            chunk_overlap=10,
        ),
    )

    assert len(chunks) == 3
    assert chunks[0] == "A" * 40
    assert chunks[1] == "B" * 40
    assert chunks[2] == "C" * 40


def test_build_default_ingestion_chunks_returns_records() -> None:
    chunk_records = build_default_ingestion_chunks()
    expected_documents = {
        document.source_id: document for document in DEFAULT_INGESTION_DOCUMENTS
    }
    seen_source_ids = {record.source_id for record in chunk_records}

    assert len(chunk_records) >= 2
    assert all(record.chunk_id for record in chunk_records)
    assert all(record.source_id for record in chunk_records)
    assert all(record.text.strip() for record in chunk_records)
    assert seen_source_ids == set(expected_documents)

    for record in chunk_records:
        expected_document = expected_documents[record.source_id]
        assert record.title == expected_document.title
        assert record.metadata["content_type"] == expected_document.content_type
        assert record.metadata["tags"] == list(expected_document.tags)
        assert record.metadata["jurisdiction"] == expected_document.jurisdiction
        assert record.metadata["access_level"] == expected_document.access_level
        assert record.metadata["file_path"] == expected_document.file_path


def test_build_vector_document_record_preserves_chunk_fields() -> None:
    chunk_record = IngestionChunkRecord(
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
        },
    )

    vector_record = build_vector_document_record(
        chunk_record=chunk_record,
        embedding=[0.1, 0.2, 0.3],
    )

    assert vector_record.chunk_id == chunk_record.chunk_id
    assert vector_record.source_id == chunk_record.source_id
    assert vector_record.title == chunk_record.title
    assert vector_record.text == chunk_record.text
    assert vector_record.embedding == [0.1, 0.2, 0.3]
    assert vector_record.metadata == chunk_record.metadata
    assert vector_record.metadata is not chunk_record.metadata


def test_build_vector_document_records_builds_parallel_batch() -> None:
    chunk_records = [
        IngestionChunkRecord(
            chunk_id="chunk-1",
            source_id="source-1",
            title="Doc 1",
            chunk_index=0,
            text="First chunk text.",
            metadata={"tag": "alpha"},
        ),
        IngestionChunkRecord(
            chunk_id="chunk-2",
            source_id="source-2",
            title="Doc 2",
            chunk_index=1,
            text="Second chunk text.",
            metadata={"tag": "beta"},
        ),
    ]

    vector_records = build_vector_document_records(
        chunk_records=chunk_records,
        embeddings=[
            [0.1, 0.2],
            [0.3, 0.4],
        ],
    )

    assert len(vector_records) == 2
    assert vector_records[0].chunk_id == "chunk-1"
    assert vector_records[0].embedding == [0.1, 0.2]
    assert vector_records[1].chunk_id == "chunk-2"
    assert vector_records[1].embedding == [0.3, 0.4]
    assert vector_records[0].metadata == {"tag": "alpha"}
    assert vector_records[1].metadata == {"tag": "beta"}


def test_build_vector_document_records_raises_on_length_mismatch() -> None:
    chunk_records = [
        IngestionChunkRecord(
            chunk_id="chunk-1",
            source_id="source-1",
            title="Doc 1",
            chunk_index=0,
            text="First chunk text.",
            metadata={"tag": "alpha"},
        ),
        IngestionChunkRecord(
            chunk_id="chunk-2",
            source_id="source-2",
            title="Doc 2",
            chunk_index=1,
            text="Second chunk text.",
            metadata={"tag": "beta"},
        ),
    ]

    with pytest.raises(ValueError, match="same length"):
        build_vector_document_records(
            chunk_records=chunk_records,
            embeddings=[
                [0.1, 0.2],
            ],
        )


def test_build_embedding_request_collects_chunk_texts() -> None:
    chunk_records = [
        IngestionChunkRecord(
            chunk_id="chunk-1",
            source_id="source-1",
            title="Doc 1",
            chunk_index=0,
            text="First chunk text.",
            metadata={"tag": "alpha"},
        ),
        IngestionChunkRecord(
            chunk_id="chunk-2",
            source_id="source-2",
            title="Doc 2",
            chunk_index=1,
            text="Second chunk text.",
            metadata={"tag": "beta"},
        ),
    ]

    embedding_request = build_embedding_request(
        chunk_records=chunk_records,
        embedding_config=EmbeddingConfig(
            provider="mock",
            model_name="mock-embedding-model",
            vector_dimensions=2,
        ),
    )

    assert embedding_request.texts == [
        "First chunk text.",
        "Second chunk text.",
    ]
    assert embedding_request.config.provider == "mock"
    assert embedding_request.config.model_name == "mock-embedding-model"
    assert embedding_request.config.vector_dimensions == 2


def test_build_vector_documents_from_embedding_response_returns_records() -> None:
    chunk_records = [
        IngestionChunkRecord(
            chunk_id="chunk-1",
            source_id="source-1",
            title="Doc 1",
            chunk_index=0,
            text="First chunk text.",
            metadata={"tag": "alpha"},
        ),
        IngestionChunkRecord(
            chunk_id="chunk-2",
            source_id="source-2",
            title="Doc 2",
            chunk_index=1,
            text="Second chunk text.",
            metadata={"tag": "beta"},
        ),
    ]

    embedding_response = EmbeddingResponse(
        vectors=[
            [0.1, 0.2],
            [0.3, 0.4],
        ],
        model_name="mock-embedding-model",
    )

    vector_records = build_vector_documents_from_embedding_response(
        chunk_records=chunk_records,
        embedding_response=embedding_response,
    )

    assert len(vector_records) == 2
    assert vector_records[0].chunk_id == "chunk-1"
    assert vector_records[0].embedding == [0.1, 0.2]
    assert vector_records[1].chunk_id == "chunk-2"
    assert vector_records[1].embedding == [0.3, 0.4]


def test_build_vector_documents_with_provider_returns_records() -> None:
    chunk_records = [
        IngestionChunkRecord(
            chunk_id="chunk-1",
            source_id="source-1",
            title="Doc 1",
            chunk_index=0,
            text="First chunk text.",
            metadata={"tag": "alpha"},
        ),
        IngestionChunkRecord(
            chunk_id="chunk-2",
            source_id="source-2",
            title="Doc 2",
            chunk_index=1,
            text="Second chunk text.",
            metadata={"tag": "beta"},
        ),
    ]

    vector_records = build_vector_documents_with_provider(
        chunk_records=chunk_records,
        embedding_config=EmbeddingConfig(
            provider="mock",
            model_name="mock-embedding-model",
            vector_dimensions=4,
        ),
        embedding_provider=MockEmbeddingProvider(),
    )

    assert len(vector_records) == 2
    assert vector_records[0].chunk_id == "chunk-1"
    assert vector_records[1].chunk_id == "chunk-2"
    assert len(vector_records[0].embedding) == 4
    assert len(vector_records[1].embedding) == 4
    assert vector_records[0].metadata == {"tag": "alpha"}
    assert vector_records[1].metadata == {"tag": "beta"}


def test_build_default_vector_documents_returns_vectorized_records() -> None:
    vector_records = build_default_vector_documents()

    assert len(vector_records) >= 2
    assert all(record.chunk_id for record in vector_records)
    assert all(record.source_id for record in vector_records)
    assert all(record.text.strip() for record in vector_records)
    assert all(len(record.embedding) == 4 for record in vector_records)
    assert all(record.metadata["access_level"] == "internal" for record in vector_records)


def test_build_default_ingestion_batch_result_returns_full_batch_result() -> None:
    batch_result = build_default_ingestion_batch_result()

    assert len(batch_result.chunk_records) >= 2
    assert len(batch_result.vector_records) == len(batch_result.chunk_records)
    assert batch_result.embedding_model_name == "mock-embedding-model"
    assert batch_result.chunk_count == len(batch_result.chunk_records)
    assert batch_result.vector_count == len(batch_result.vector_records)
    assert all(record.text.strip() for record in batch_result.chunk_records)
    assert all(len(record.embedding) == 4 for record in batch_result.vector_records)
