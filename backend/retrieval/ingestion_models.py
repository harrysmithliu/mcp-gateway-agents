from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class KnowledgeSourceDocument:
    """Represents a raw knowledge document that is ready for ingestion."""

    source_id: str
    title: str
    file_path: str
    content_type: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    jurisdiction: str | None = None
    access_level: str = "internal"


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """Defines how documents should be chunked in the current ingestion batch."""

    chunk_size: int
    chunk_overlap: int
    splitter_type: str = "recursive_character"


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    """Describes the embedding configuration to use later, without invoking it yet."""

    provider: str
    model_name: str
    vector_dimensions: int
    query_prefix: str = ""


@dataclass(frozen=True, slots=True)
class IngestionChunkRecord:
    """Represents a standard chunk record after chunking and before vector storage."""
    """It has already been chunked, but has not been embedded yet."""

    chunk_id: str
    source_id: str
    title: str
    chunk_index: int
    text: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VectorDocumentRecord:
    """Represents one embedded chunk that is ready for vector persistence."""
    """It already has an embedding, so the next step is to write it into a vector store such as pgvector."""

    chunk_id: str
    source_id: str
    title: str
    text: str
    embedding: list[float]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    """Represents a batch embedding request built from ingestion chunk records."""

    texts: list[str]
    config: EmbeddingConfig


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    """Represents embedding vectors returned for one batch request."""

    vectors: list[list[float]]
    model_name: str


@dataclass(frozen=True, slots=True)
class IngestionBatchResult:
    """Represents the in-memory result of one ingestion batch run."""

    chunk_records: list[IngestionChunkRecord]
    vector_records: list[VectorDocumentRecord]
    embedding_model_name: str
    chunk_count: int
    vector_count: int
