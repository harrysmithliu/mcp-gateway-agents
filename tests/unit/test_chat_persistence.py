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


class FakeStorageBundle:
    def __init__(self) -> None:
        self.chat_session_repository = FakeChatSessionRepository()
        self.chat_message_repository = FakeChatMessageRepository()
        self.tool_call_log_repository = FakeToolCallLogRepository()
        self.audit_event_repository = FakeAuditEventRepository()
        self.risk_alert_repository = FakeRiskAlertRepository()


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
    coordinator = ChatPersistenceCoordinator(storage_bundle=storage_bundle)

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


def test_chat_persistence_coordinator_finishes_exchange_with_noop_result() -> None:
    storage_bundle = FakeStorageBundle()
    coordinator = ChatPersistenceCoordinator(storage_bundle=storage_bundle)
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
    )
    assert len(storage_bundle.chat_message_repository.records) == 2
    assert storage_bundle.chat_message_repository.records[1].sender_type == "assistant"
    assert storage_bundle.chat_message_repository.records[1].message_text == "placeholder"
    assert storage_bundle.audit_event_repository.records[0].event_type == "chat_exchange_completed"


def test_chat_persistence_coordinator_generates_session_id_when_missing() -> None:
    storage_bundle = FakeStorageBundle()
    coordinator = ChatPersistenceCoordinator(storage_bundle=storage_bundle)

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
    coordinator = ChatPersistenceCoordinator(storage_bundle=FailingStorageBundle())

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
        tool_logs_persisted=True,
        audit_events_persisted=True,
        operational_records_persisted=True,
    )


def test_chat_persistence_coordinator_tolerates_message_write_failures() -> None:
    coordinator = ChatPersistenceCoordinator(storage_bundle=MessageFailingStorageBundle())

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
        assistant_message_persisted=False,
        tool_logs_persisted=True,
        audit_events_persisted=True,
        operational_records_persisted=True,
    )


def test_chat_persistence_coordinator_persists_tool_logs_and_audit_event() -> None:
    storage_bundle = FakeStorageBundle()
    coordinator = ChatPersistenceCoordinator(storage_bundle=storage_bundle)
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
    assert storage_bundle.risk_alert_repository.records == []


def test_chat_persistence_coordinator_tolerates_tool_log_write_failures() -> None:
    coordinator = ChatPersistenceCoordinator(storage_bundle=ToolLogFailingStorageBundle())
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
    coordinator = ChatPersistenceCoordinator(storage_bundle=AuditFailingStorageBundle())
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
    coordinator = ChatPersistenceCoordinator(storage_bundle=storage_bundle)
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
    coordinator = ChatPersistenceCoordinator(storage_bundle=OpsRecordFailingStorageBundle())
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
