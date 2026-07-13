import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.models import AgentResponse, ChatCommand, ChatHistoryMessage
from backend.mcp_gateway.models import ToolInvocationResult
from backend.storage.chat_persistence import (
    ChatPersistenceCoordinator,
    ChatPersistenceResult,
)
from backend.storage.db import SQLStatement
from backend.storage.redis_chat_context import RedisChatContextStore
from backend.storage.models import (
    AuditEventRecord,
    ChatMessageRecord,
    ChatSessionRecord,
    RiskAlertRecord,
    ToolCallLogRecord,
)


class FakeChatSessionRepository:
    def __init__(self) -> None:
        self.records: list[ChatSessionRecord] = []
        self.existing_sessions: dict[str, dict[str, object]] = {}

    def create_session(self, record: ChatSessionRecord) -> SQLStatement:
        self.records.append(record)
        return SQLStatement(
            sql="INSERT INTO convo.chat_sessions (...) ON CONFLICT DO NOTHING",
            params={
                "session_id": record.session_id,
                "user_id": record.user_id,
                "session_title": record.session_title,
            },
        )

    def get_session(self, session_id: str) -> dict[str, object] | None:
        return self.existing_sessions.get(session_id)

    def claim_session(self, session_id: str, user_id: int) -> SQLStatement:
        self.existing_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
        }
        return SQLStatement(
            sql="UPDATE convo.chat_sessions SET user_id = %(user_id)s",
            params={"session_id": session_id, "user_id": user_id},
        )


class FakeStorageBundle:
    def __init__(self) -> None:
        self.chat_session_repository = FakeChatSessionRepository()
        self.chat_message_repository = FakeChatMessageRepository()
        self.tool_call_log_repository = FakeToolCallLogRepository()
        self.audit_event_repository = FakeAuditEventRepository()
        self.risk_alert_repository = FakeRiskAlertRepository()


class FakeRedisChatContextStore:
    def __init__(self) -> None:
        self.messages_by_session: dict[str, list[ChatHistoryMessage]] = {}
        self.append_calls: list[tuple[str | None, str, str]] = []

    def load_recent_messages(
        self,
        session_id: str | None,
        limit: int | None = None,
    ) -> list[ChatHistoryMessage]:
        if session_id is None:
            return []
        messages = list(self.messages_by_session.get(session_id, []))
        if limit is None:
            return messages
        return messages[-limit:]

    def append_message(
        self,
        session_id: str | None,
        role: str,
        content: str,
        user_id: int | None = None,
    ) -> bool:
        _ = user_id
        self.append_calls.append((session_id, role, content))
        if session_id is None:
            return False
        self.messages_by_session.setdefault(session_id, []).append(
            ChatHistoryMessage(role=role, content=content)
        )
        return True


class FailingRedisChatContextStore:
    def load_recent_messages(
        self,
        session_id: str | None,
        limit: int | None = None,
    ) -> list[ChatHistoryMessage]:
        _ = session_id, limit
        return []

    def append_message(
        self,
        session_id: str | None,
        role: str,
        content: str,
    ) -> bool:
        _ = session_id, role, content
        return False


class FakeChatMessageRepository:
    def __init__(self) -> None:
        self.records: list[ChatMessageRecord] = []

    def append_message(self, record: ChatMessageRecord) -> SQLStatement:
        self.records.append(record)
        return SQLStatement(
            sql="INSERT INTO convo.chat_messages (...)",
            params={
                "message_id": record.message_id,
                "session_id": record.session_id,
                "sender_type": record.sender_type,
                "message_text": record.message_text,
            },
        )


class FakeToolCallLogRepository:
    def __init__(self) -> None:
        self.records: list[ToolCallLogRecord] = []

    def create_tool_call_log(self, record: ToolCallLogRecord) -> SQLStatement:
        self.records.append(record)
        return SQLStatement(
            sql="INSERT INTO audit.tool_call_logs (...)",
            params={
                "tool_call_id": record.tool_call_id,
                "session_id": record.session_id,
                "message_id": record.message_id,
                "tool_namespace": record.tool_namespace,
                "tool_name": record.tool_name,
                "call_status": record.call_status,
            },
        )


class FakeAuditEventRepository:
    def __init__(self) -> None:
        self.records: list[AuditEventRecord] = []

    def create_audit_event(self, record: AuditEventRecord) -> SQLStatement:
        self.records.append(record)
        return SQLStatement(
            sql="INSERT INTO audit.audit_events (...)",
            params={
                "event_id": record.event_id,
                "event_type": record.event_type,
                "event_summary": record.event_summary,
            },
        )


class FakeRiskAlertRepository:
    def __init__(self) -> None:
        self.records: list[RiskAlertRecord] = []

    def create_risk_alert(self, record: RiskAlertRecord) -> SQLStatement:
        self.records.append(record)
        return SQLStatement(
            sql="INSERT INTO risk.risk_alerts (...)",
            params={
                "alert_id": record.alert_id,
                "session_id": record.session_id,
                "message_id": record.message_id,
                "alert_type": record.alert_type,
                "severity": record.severity,
                "status": record.status,
            },
        )


class FailingChatSessionRepository:
    def create_session(self, record: ChatSessionRecord) -> SQLStatement:
        _ = record
        raise RuntimeError("db unavailable")


class FailingStorageBundle:
    def __init__(self) -> None:
        self.chat_session_repository = FailingChatSessionRepository()
        self.chat_message_repository = FakeChatMessageRepository()
        self.tool_call_log_repository = FakeToolCallLogRepository()
        self.audit_event_repository = FakeAuditEventRepository()
        self.risk_alert_repository = FakeRiskAlertRepository()


class FailingChatMessageRepository:
    def append_message(self, record: ChatMessageRecord) -> SQLStatement:
        _ = record
        raise RuntimeError("db unavailable")


class MessageFailingStorageBundle:
    def __init__(self) -> None:
        self.chat_session_repository = FakeChatSessionRepository()
        self.chat_message_repository = FailingChatMessageRepository()
        self.tool_call_log_repository = FakeToolCallLogRepository()
        self.audit_event_repository = FakeAuditEventRepository()
        self.risk_alert_repository = FakeRiskAlertRepository()


class FailingToolCallLogRepository:
    def create_tool_call_log(self, record: ToolCallLogRecord) -> SQLStatement:
        _ = record
        raise RuntimeError("db unavailable")


class FailingAuditEventRepository:
    def create_audit_event(self, record: AuditEventRecord) -> SQLStatement:
        _ = record
        raise RuntimeError("db unavailable")


class ToolLogFailingStorageBundle:
    def __init__(self) -> None:
        self.chat_session_repository = FakeChatSessionRepository()
        self.chat_message_repository = FakeChatMessageRepository()
        self.tool_call_log_repository = FailingToolCallLogRepository()
        self.audit_event_repository = FakeAuditEventRepository()
        self.risk_alert_repository = FakeRiskAlertRepository()


class AuditFailingStorageBundle:
    def __init__(self) -> None:
        self.chat_session_repository = FakeChatSessionRepository()
        self.chat_message_repository = FakeChatMessageRepository()
        self.tool_call_log_repository = FakeToolCallLogRepository()
        self.audit_event_repository = FailingAuditEventRepository()
        self.risk_alert_repository = FakeRiskAlertRepository()


class FailingRiskAlertRepository:
    def create_risk_alert(self, record: RiskAlertRecord) -> SQLStatement:
        _ = record
        raise RuntimeError("db unavailable")


class OpsRecordFailingStorageBundle:
    def __init__(self) -> None:
        self.chat_session_repository = FakeChatSessionRepository()
        self.chat_message_repository = FakeChatMessageRepository()
        self.tool_call_log_repository = FakeToolCallLogRepository()
        self.audit_event_repository = FakeAuditEventRepository()
        self.risk_alert_repository = FailingRiskAlertRepository()


def test_chat_persistence_coordinator_starts_exchange_from_chat_command() -> None:
    storage_bundle = FakeStorageBundle()
    redis_store = FakeRedisChatContextStore()
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=storage_bundle,
        redis_chat_context_store=redis_store,
    )

    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="Analyst",
            message_text="Review this account.",
            session_id="session-round-1",
            recent_messages=[
                ChatHistoryMessage(role="user", content="Earlier question"),
            ],
        ),
        normalized_role="analyst",
        normalized_text="Review this account.",
    )

    assert exchange.user_role == "Analyst"
    assert exchange.normalized_role == "analyst"
    assert exchange.message_text == "Review this account."
    assert exchange.normalized_text == "Review this account."
    assert exchange.requested_session_id == "session-round-1"
    assert exchange.effective_session_id == "session-round-1"
    assert exchange.session_persisted is True
    assert exchange.user_message_persisted is True
    assert exchange.write_order == [
        "ensure_chat_session",
        "append_user_message",
        "persist_redis_user_message",
    ]
    assert exchange.redis_context_persisted is True
    assert exchange.recent_messages == [
        ChatHistoryMessage(role="user", content="Earlier question")
    ]
    assert storage_bundle.chat_session_repository.records == [
        ChatSessionRecord(
            session_id="session-round-1",
            user_id=None,
            session_title="Review this account.",
        )
    ]
    assert len(storage_bundle.chat_message_repository.records) == 1
    assert storage_bundle.chat_message_repository.records[0].session_id == "session-round-1"
    assert storage_bundle.chat_message_repository.records[0].sender_type == "user"
    assert storage_bundle.chat_message_repository.records[0].message_text == "Review this account."
    assert redis_store.messages_by_session["session-round-1"] == [
        ChatHistoryMessage(role="user", content="Review this account.")
    ]


def test_chat_persistence_coordinator_rejects_foreign_owned_session() -> None:
    storage_bundle = FakeStorageBundle()
    storage_bundle.chat_session_repository.existing_sessions["session-owned"] = {
        "session_id": "session-owned",
        "user_id": 202,
    }
    coordinator = ChatPersistenceCoordinator(storage_bundle=storage_bundle)

    import pytest

    with pytest.raises(PermissionError):
        coordinator.start_exchange(
            command=ChatCommand(
                user_role="analyst",
                message_text="Review this account.",
                session_id="session-owned",
                user_id=101,
            ),
            normalized_role="analyst",
            normalized_text="Review this account.",
        )


def test_chat_persistence_coordinator_finishes_exchange_with_noop_result() -> None:
    storage_bundle = FakeStorageBundle()
    redis_store = FakeRedisChatContextStore()
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=storage_bundle,
        redis_chat_context_store=redis_store,
    )
    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Review this account.",
            session_id="session-round-1",
        ),
        normalized_role="analyst",
        normalized_text="Review this account.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(reply_text="placeholder"),
    )

    assert result == ChatPersistenceResult(
        session_persisted=True,
        user_message_persisted=True,
        assistant_message_persisted=True,
        tool_logs_persisted=True,
        audit_events_persisted=True,
        operational_records_persisted=True,
        redis_context_persisted=True,
        write_order=[
            "ensure_chat_session",
            "append_user_message",
            "persist_redis_user_message",
            "append_assistant_message",
            "persist_redis_assistant_message",
            "persist_tool_invocation_logs",
            "persist_operational_records",
            "persist_audit_events",
        ],
    )
    assert len(storage_bundle.chat_message_repository.records) == 2
    assert storage_bundle.chat_message_repository.records[1].sender_type == "assistant"
    assert storage_bundle.chat_message_repository.records[1].message_text == "placeholder"
    assert storage_bundle.audit_event_repository.records[0].event_type == "chat_exchange_completed"
    assert redis_store.messages_by_session["session-round-1"] == [
        ChatHistoryMessage(role="user", content="Review this account."),
        ChatHistoryMessage(role="assistant", content="placeholder"),
    ]


def test_chat_persistence_coordinator_generates_session_id_when_missing() -> None:
    storage_bundle = FakeStorageBundle()
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=storage_bundle,
        redis_chat_context_store=FakeRedisChatContextStore(),
    )

    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Review this account.",
            session_id=None,
        ),
        normalized_role="analyst",
        normalized_text="Review this account.",
    )

    assert exchange.requested_session_id is None
    assert exchange.effective_session_id is not None
    assert exchange.session_persisted is True
    assert exchange.user_message_persisted is True
    assert storage_bundle.chat_session_repository.records[0].session_id == exchange.effective_session_id


def test_chat_persistence_coordinator_keeps_main_flow_alive_when_write_fails() -> None:
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=FailingStorageBundle(),
        redis_chat_context_store=FakeRedisChatContextStore(),
    )

    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Review this account.",
            session_id="session-round-2-failure",
        ),
        normalized_role="analyst",
        normalized_text="Review this account.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(reply_text="placeholder"),
    )

    assert exchange.effective_session_id == "session-round-2-failure"
    assert exchange.session_persisted is False
    assert exchange.session_persistence_error == "chat_session_write_failed"
    assert exchange.user_message_persisted is False
    assert exchange.user_message_persistence_error == "chat_session_not_persisted"
    assert result == ChatPersistenceResult(
        session_persisted=False,
        session_persistence_error="chat_session_write_failed",
        user_message_persistence_error="chat_session_not_persisted",
        assistant_message_persistence_error="chat_session_not_persisted",
        tool_logs_persisted=True,
        audit_events_persisted=False,
        audit_events_persistence_error="audit_events_skipped_missing_session",
        operational_records_persisted=True,
        redis_context_persisted=True,
        write_order=[
            "ensure_chat_session",
            "append_user_message",
            "persist_redis_user_message",
            "append_assistant_message",
            "persist_redis_assistant_message",
            "persist_tool_invocation_logs",
            "persist_operational_records",
            "persist_audit_events",
        ],
    )


def test_chat_persistence_coordinator_tolerates_message_write_failures() -> None:
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=MessageFailingStorageBundle(),
        redis_chat_context_store=FakeRedisChatContextStore(),
    )

    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Review this account.",
            session_id="session-round-3-failure",
        ),
        normalized_role="analyst",
        normalized_text="Review this account.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(reply_text="placeholder"),
    )

    assert exchange.session_persisted is True
    assert exchange.user_message_persisted is False
    assert exchange.user_message_persistence_error == "user_message_write_failed"
    assert exchange.assistant_message_persisted is False
    assert exchange.assistant_message_persistence_error == "assistant_message_write_failed"
    assert result == ChatPersistenceResult(
        session_persisted=True,
        user_message_persisted=False,
        user_message_persistence_error="user_message_write_failed",
        assistant_message_persisted=False,
        assistant_message_persistence_error="assistant_message_write_failed",
        tool_logs_persisted=True,
        audit_events_persisted=True,
        operational_records_persisted=True,
        redis_context_persisted=True,
        write_order=[
            "ensure_chat_session",
            "append_user_message",
            "persist_redis_user_message",
            "append_assistant_message",
            "persist_redis_assistant_message",
            "persist_tool_invocation_logs",
            "persist_operational_records",
            "persist_audit_events",
        ],
    )


def test_chat_persistence_coordinator_persists_tool_logs_and_audit_event() -> None:
    storage_bundle = FakeStorageBundle()
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=storage_bundle,
        redis_chat_context_store=FakeRedisChatContextStore(),
    )
    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Search the policy playbook and score this account.",
            session_id="session-round-4",
        ),
        normalized_role="analyst",
        normalized_text="Search the policy playbook and score this account.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(
            reply_text="placeholder",
            tool_names=["knowledge.search", "risk.score_account"],
            tool_invocation_results=[
                ToolInvocationResult(
                    tool_name="knowledge.search",
                    domain="knowledge",
                    invocation_status="completed",
                    request_payload={"query": "policy"},
                    response_payload={"total_matches": 1},
                ),
                ToolInvocationResult(
                    tool_name="risk.score_account",
                    domain="risk",
                    invocation_status="completed",
                    request_payload={"account_id": "A-1"},
                    response_payload={"score": 0.82},
                ),
            ],
        ),
    )

    assert result.tool_logs_persisted is True
    assert result.audit_events_persisted is True
    assert result.write_order == [
        "ensure_chat_session",
        "append_user_message",
        "persist_redis_user_message",
        "append_assistant_message",
        "persist_redis_assistant_message",
        "persist_tool_invocation_logs",
        "persist_operational_records",
        "persist_audit_events",
    ]
    assert len(storage_bundle.tool_call_log_repository.records) == 2
    assert {
        record.tool_name for record in storage_bundle.tool_call_log_repository.records
    } == {"knowledge.search", "risk.score_account"}
    assert all(
        record.message_id == exchange.user_message_id
        for record in storage_bundle.tool_call_log_repository.records
    )
    assert len(storage_bundle.audit_event_repository.records) == 1
    audit_event = storage_bundle.audit_event_repository.records[0]
    assert audit_event.event_type == "chat_exchange_completed"
    assert audit_event.event_payload["session_id"] == "session-round-4"
    assert audit_event.event_payload["tool_invocation_count"] == 2
    assert audit_event.event_payload["write_order"] == result.write_order
    assert storage_bundle.risk_alert_repository.records == []


def test_chat_persistence_coordinator_tolerates_tool_log_write_failures() -> None:
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=ToolLogFailingStorageBundle(),
        redis_chat_context_store=FakeRedisChatContextStore(),
    )
    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Search the policy playbook.",
            session_id="session-round-4-tool-log-failure",
        ),
        normalized_role="analyst",
        normalized_text="Search the policy playbook.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(
            reply_text="placeholder",
            tool_names=["knowledge.search"],
            tool_invocation_results=[
                ToolInvocationResult(
                    tool_name="knowledge.search",
                    domain="knowledge",
                    invocation_status="completed",
                    request_payload={"query": "policy"},
                    response_payload={"total_matches": 1},
                )
            ],
        ),
    )

    assert exchange.tool_logs_persisted is False
    assert exchange.tool_logs_persistence_error == "tool_logs_write_failed"
    assert result.tool_logs_persisted is False
    assert result.audit_events_persisted is True
    assert result.operational_records_persisted is True


def test_chat_persistence_coordinator_tolerates_audit_write_failures() -> None:
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=AuditFailingStorageBundle(),
        redis_chat_context_store=FakeRedisChatContextStore(),
    )
    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Search the policy playbook.",
            session_id="session-round-4-audit-failure",
        ),
        normalized_role="analyst",
        normalized_text="Search the policy playbook.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(
            reply_text="placeholder",
            tool_names=["knowledge.search"],
            tool_invocation_results=[
                ToolInvocationResult(
                    tool_name="knowledge.search",
                    domain="knowledge",
                    invocation_status="completed",
                    request_payload={"query": "policy"},
                    response_payload={"total_matches": 1},
                )
            ],
        ),
    )

    assert exchange.audit_events_persisted is False
    assert exchange.audit_events_persistence_error == "audit_events_write_failed"
    assert result.tool_logs_persisted is True
    assert result.audit_events_persisted is False
    assert result.operational_records_persisted is True


def test_chat_persistence_coordinator_persists_operational_record_from_ops_tool() -> None:
    storage_bundle = FakeStorageBundle()
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=storage_bundle,
        redis_chat_context_store=FakeRedisChatContextStore(),
    )
    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Escalate this suspicious risk review.",
            session_id="session-round-5",
        ),
        normalized_role="analyst",
        normalized_text="Escalate this suspicious risk review.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(
            reply_text="placeholder",
            tool_names=["ops.create_alert_or_action"],
            tool_invocation_results=[
                ToolInvocationResult(
                    tool_name="ops.create_alert_or_action",
                    domain="operations",
                    invocation_status="completed",
                    request_payload={"query": "escalate suspicious risk review"},
                    response_payload={
                        "recommended_action": {
                            "template_id": "ops-alert-escalation",
                            "action_type": "alert",
                            "severity": "high",
                            "summary_template": "Escalate suspicious trading activity.",
                        },
                        "templates": [
                            {
                                "template_id": "ops-alert-escalation",
                                "action_type": "alert",
                            }
                        ],
                    },
                )
            ],
        ),
    )

    assert result.operational_records_persisted is True
    assert len(storage_bundle.risk_alert_repository.records) == 1
    alert_record = storage_bundle.risk_alert_repository.records[0]
    assert alert_record.session_id == "session-round-5"
    assert alert_record.message_id == exchange.assistant_message_id
    assert alert_record.alert_type == "alert"
    assert alert_record.severity == "high"
    assert alert_record.status == "open"
    assert (
        alert_record.details["recommended_action"]["template_id"]
        == "ops-alert-escalation"
    )


def test_chat_persistence_coordinator_tolerates_operational_record_failures() -> None:
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=OpsRecordFailingStorageBundle(),
        redis_chat_context_store=FakeRedisChatContextStore(),
    )
    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Escalate this suspicious risk review.",
            session_id="session-round-5-failure",
        ),
        normalized_role="analyst",
        normalized_text="Escalate this suspicious risk review.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(
            reply_text="placeholder",
            tool_names=["ops.create_alert_or_action"],
            tool_invocation_results=[
                ToolInvocationResult(
                    tool_name="ops.create_alert_or_action",
                    domain="operations",
                    invocation_status="completed",
                    request_payload={"query": "escalate suspicious risk review"},
                    response_payload={
                        "recommended_action": {
                            "template_id": "ops-alert-escalation",
                            "action_type": "alert",
                            "severity": "high",
                            "summary_template": "Escalate suspicious trading activity.",
                        }
                    },
                )
            ],
        ),
    )

    assert exchange.operational_records_persisted is False
    assert (
        exchange.operational_records_persistence_error
        == "operational_records_write_failed"
    )
    assert result.operational_records_persisted is False


def test_chat_persistence_coordinator_skips_tool_logs_without_user_message_anchor() -> None:
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=MessageFailingStorageBundle(),
        redis_chat_context_store=FakeRedisChatContextStore(),
    )
    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Search the policy playbook.",
            session_id="session-round-6-tool-skip",
        ),
        normalized_role="analyst",
        normalized_text="Search the policy playbook.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(
            reply_text="placeholder",
            tool_names=["knowledge.search"],
            tool_invocation_results=[
                ToolInvocationResult(
                    tool_name="knowledge.search",
                    domain="knowledge",
                    invocation_status="completed",
                    request_payload={"query": "policy"},
                    response_payload={"total_matches": 1},
                )
            ],
        ),
    )

    assert result.tool_logs_persisted is False
    assert (
        result.tool_logs_persistence_error
        == "tool_logs_skipped_missing_user_message"
    )
    assert result.audit_events_persisted is True


def test_chat_persistence_coordinator_skips_operational_record_without_assistant_message() -> None:
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=MessageFailingStorageBundle(),
        redis_chat_context_store=FakeRedisChatContextStore(),
    )
    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Escalate this suspicious risk review.",
            session_id="session-round-6-ops-skip",
        ),
        normalized_role="analyst",
        normalized_text="Escalate this suspicious risk review.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(
            reply_text="placeholder",
            tool_names=["ops.create_alert_or_action"],
            tool_invocation_results=[
                ToolInvocationResult(
                    tool_name="ops.create_alert_or_action",
                    domain="operations",
                    invocation_status="completed",
                    request_payload={"query": "escalate suspicious risk review"},
                    response_payload={
                        "recommended_action": {
                            "template_id": "ops-alert-escalation",
                            "action_type": "alert",
                            "severity": "high",
                            "summary_template": "Escalate suspicious trading activity.",
                        }
                    },
                )
            ],
        ),
    )

    assert result.operational_records_persisted is False
    assert (
        result.operational_records_persistence_error
        == "operational_records_skipped_missing_assistant_message"
    )
    assert result.audit_events_persisted is True


def test_chat_persistence_coordinator_tolerates_redis_context_failures() -> None:
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=FakeStorageBundle(),
        redis_chat_context_store=FailingRedisChatContextStore(),
    )
    exchange = coordinator.start_exchange(
        command=ChatCommand(
            user_role="analyst",
            message_text="Review this account.",
            session_id="session-round-7-redis-failure",
        ),
        normalized_role="analyst",
        normalized_text="Review this account.",
    )

    result = coordinator.finish_exchange(
        exchange=exchange,
        agent_response=AgentResponse(reply_text="placeholder"),
    )

    assert exchange.redis_context_persisted is False
    assert exchange.redis_context_persistence_error == "redis_context_write_failed"
    assert result.redis_context_persisted is False
    assert result.redis_context_persistence_error == "redis_context_write_failed"
