from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ChatSessionRecord:
    session_id: str
    user_id: int
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
