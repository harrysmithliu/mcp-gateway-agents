from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Normalized input contract for one knowledge retrieval request."""

    text: str
    top_k: int = 5
    access_level: str | None = None
    jurisdiction: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    allowed_access_levels: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        normalized_text = self.text.strip()
        if not normalized_text:
            raise ValueError("retrieval query text must not be empty")
        if not 1 <= self.top_k <= 50:
            raise ValueError("retrieval query top_k must be between 1 and 50")
        object.__setattr__(self, "text", normalized_text)
        object.__setattr__(
            self,
            "allowed_access_levels",
            tuple(dict.fromkeys(
                level.strip()
                for level in self.allowed_access_levels
                if isinstance(level, str) and level.strip()
            )),
        )

    @property
    def effective_access_levels(self) -> tuple[str, ...]:
        if self.allowed_access_levels:
            return self.allowed_access_levels
        if self.access_level:
            return (self.access_level,)
        return ()


@dataclass(frozen=True, slots=True)
class QueryEmbedding:
    """Embedding produced for a retrieval query and ready for vector search."""

    vector: list[float]
    provider: str
    model_name: str
    vector_dimensions: int


@dataclass(frozen=True, slots=True)
class RetrievalChunk:
    """A ranked knowledge chunk returned by the retrieval layer."""

    document_id: str
    title: str
    summary: str
    chunk_id: str | None = None
    chunk_index: int | None = None
    source_path: str | None = None
    score: float | None = None
    matched_terms: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalCitation:
    """Stable source reference that can be shown to an agent or user."""

    document_id: str
    title: str
    chunk_id: str | None = None
    chunk_index: int | None = None
    source_path: str | None = None
    score: float | None = None
    excerpt: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalMetadata:
    """Operational metadata for one retrieval result without raw vectors."""

    provider: str | None = None
    model_name: str | None = None
    vector_dimensions: int | None = None
    top_k: int = 0
    result_count: int = 0
    filters: dict[str, object] = field(default_factory=dict)
    status: str = "completed"
    latency_ms: int = 0
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalRuntimeStatus:
    """Safe application-level status for the configured retrieval capability."""

    state: str
    enabled: bool
    vector_backend: str
    provider: str | None = None
    model_name: str | None = None
    vector_dimensions: int | None = None
    reason: str | None = None

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Planner-facing retrieval result contract shared by API and Agent layers."""

    rag_enabled: bool
    retrieval_source: str
    retrieved_chunks: list[RetrievalChunk] = field(default_factory=list)
    citations: list[RetrievalCitation] = field(default_factory=list)
    metadata: RetrievalMetadata = field(default_factory=RetrievalMetadata)

    def to_payload(self) -> dict[str, object]:
        return {
            "rag_enabled": self.rag_enabled,
            "retrieval_source": self.retrieval_source,
            "retrieved_chunks": [asdict(chunk) for chunk in self.retrieved_chunks],
            "citations": [asdict(citation) for citation in self.citations],
            "retrieval_metadata": asdict(self.metadata),
        }


# Keep the current Agent-facing name while the read path moves to a result contract.
RetrievalContext = RetrievalResult
