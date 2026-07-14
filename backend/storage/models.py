from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ChatSessionRecord:
    session_id: str
    user_id: int | None
    session_title: str


@dataclass(frozen=True, slots=True)
class ChatMessageRecord:
    message_id: str
    session_id: str
    sender_type: str
    message_text: str


@dataclass(frozen=True, slots=True)
class ToolCallLogRecord:
    tool_call_id: str
    tool_namespace: str
    tool_name: str
    call_status: str
    request_payload: dict[str, object] = field(default_factory=dict)
    response_payload: dict[str, object] = field(default_factory=dict)
    session_id: str | None = None
    message_id: str | None = None
    actor_user_id: int | None = None
    error_message: str | None = None
    latency_ms: int | None = None


@dataclass(frozen=True, slots=True)
class AuditEventRecord:
    event_id: str
    event_type: str
    event_summary: str
    event_payload: dict[str, object] = field(default_factory=dict)
    actor_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class RiskAlertRecord:
    alert_id: str
    alert_type: str
    severity: str
    status: str
    summary: str
    details: dict[str, object] = field(default_factory=dict)
    session_id: str | None = None
    message_id: str | None = None
    actor_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class RiskAlertStatusEventRecord:
    event_id: str
    alert_id: str
    previous_status: str
    next_status: str
    reason: str | None = None
    details: dict[str, object] = field(default_factory=dict)
    actor_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class RiskAlertApprovalRecord:
    approval_id: str
    alert_id: str
    approval_status: str
    request_reason: str
    requested_by_user_id: int | None = None
    decided_by_user_id: int | None = None
    decision_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RiskBatchScoreRunRecord:
    run_id: str
    requested_account_count: int
    scored_account_count: int
    missing_account_count: int
    highest_risk_score: int
    average_risk_score: float
    risk_level_counts: dict[str, int] = field(default_factory=dict)
    actor_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class RiskBatchScoreResultRecord:
    result_id: str
    run_id: str
    account_id: str
    profile_id: str
    risk_score: int
    risk_level: str
    review_status: str
    exposure_usd: int
    alert_count_30d: int
    risk_flags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class KnowledgeDocumentRecord:
    document_id: str
    title: str
    content_type: str
    access_level: str
    file_path: str
    tags: list[str] = field(default_factory=list)
    jurisdiction: str | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeChunkRecord:
    chunk_id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    chunk_metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingRecord:
    chunk_id: str
    embedding_model_name: str
    embedding_provider: str
    vector_dimensions: int
    embedding: list[float] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class KnowledgeSearchRecord:
    """One database row returned by the pgvector similarity repository."""

    chunk_id: str
    document_id: str
    title: str
    source_path: str
    chunk_index: int
    chunk_text: str
    chunk_metadata: dict[str, object] = field(default_factory=dict)
    similarity_score: float = 0.0


@dataclass(frozen=True, slots=True)
class KnowledgeIngestionRunRecord:
    run_id: str
    run_mode: str
    status: str
    requested_by_user_id: int | None = None
    source_count: int = 0
    document_count: int = 0
    chunk_count: int = 0
    embedding_count: int = 0
    embedding_provider: str | None = None
    embedding_model_name: str | None = None
    vector_dimensions: int | None = None
    error_type: str | None = None
    error_summary: str | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeIngestionSourceRecord:
    run_id: str
    source_id: str
    title: str
    source_path: str
    checksum_sha256: str
    byte_size: int
    content_type: str
    access_level: str
    jurisdiction: str | None = None
    tags: list[str] = field(default_factory=list)
