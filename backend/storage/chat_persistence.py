from dataclasses import dataclass, field
from uuid import uuid4

from backend.agent.models import AgentResponse, ChatCommand, ChatHistoryMessage
from backend.storage.models import (
    AuditEventRecord,
    ChatMessageRecord,
    ChatSessionRecord,
    RiskAlertRecord,
    ToolCallLogRecord,
)
from backend.storage.redis_chat_context import RedisChatContextStore
from backend.storage.runtime import StorageBundle


@dataclass(slots=True)
class ChatPersistenceExchange:
    """Unified runtime envelope for future chat persistence stages."""

    user_role: str
    normalized_role: str
    message_text: str
    normalized_text: str
    requested_session_id: str | None
    effective_session_id: str | None
    user_message_id: str | None = None
    assistant_message_id: str | None = None
    session_persisted: bool = False
    session_persistence_error: str | None = None
    user_message_persisted: bool = False
    user_message_persistence_error: str | None = None
    assistant_message_persisted: bool = False
    assistant_message_persistence_error: str | None = None
    tool_logs_persisted: bool = False
    tool_logs_persistence_error: str | None = None
    audit_events_persisted: bool = False
    audit_events_persistence_error: str | None = None
    operational_records_persisted: bool = False
    operational_records_persistence_error: str | None = None
    redis_context_persisted: bool = False
    redis_context_persistence_error: str | None = None
    write_order: list[str] = field(default_factory=list)
    recent_messages: list[ChatHistoryMessage] = field(default_factory=list)


@dataclass(slots=True)
class ChatPersistenceResult:
    """Progress marker for staged chat persistence rollout."""

    session_persisted: bool = False
    session_persistence_error: str | None = None
    user_message_persisted: bool = False
    user_message_persistence_error: str | None = None
    assistant_message_persisted: bool = False
    assistant_message_persistence_error: str | None = None
    tool_logs_persisted: bool = False
    tool_logs_persistence_error: str | None = None
    audit_events_persisted: bool = False
    audit_events_persistence_error: str | None = None
    operational_records_persisted: bool = False
    operational_records_persistence_error: str | None = None
    redis_context_persisted: bool = False
    redis_context_persistence_error: str | None = None
    write_order: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ChatPersistenceCoordinator:
    """Single entrypoint for future chat persistence orchestration."""

    storage_bundle: StorageBundle
    redis_chat_context_store: RedisChatContextStore | None = None

    def record_stage(
        self,
        exchange: ChatPersistenceExchange,
        stage_name: str,
    ) -> None:
        exchange.write_order.append(stage_name)

    def build_session_id(
        self,
        requested_session_id: str | None,
    ) -> str:
        if requested_session_id:
            return requested_session_id
        return str(uuid4())

    def build_session_title(
        self,
        normalized_text: str,
    ) -> str:
        compact_text = " ".join(normalized_text.split())
        if not compact_text:
            return "New chat session"
        return compact_text[:80]

    def build_message_id(self) -> str:
        return str(uuid4())

    def ensure_chat_session(
        self,
        exchange: ChatPersistenceExchange,
    ) -> None:
        self.record_stage(exchange, "ensure_chat_session")
        if exchange.effective_session_id is None:
            return

        try:
            self.storage_bundle.chat_session_repository.create_session(
                ChatSessionRecord(
                    session_id=exchange.effective_session_id,
                    user_id=None,
                    session_title=self.build_session_title(exchange.normalized_text),
                )
            )
            exchange.session_persisted = True
        except Exception:
            exchange.session_persisted = False
            exchange.session_persistence_error = "chat_session_write_failed"

    def append_user_message(
        self,
        exchange: ChatPersistenceExchange,
    ) -> None:
        self.record_stage(exchange, "append_user_message")
        if exchange.effective_session_id is None:
            exchange.user_message_persistence_error = "chat_session_missing"
            self.persist_redis_context_message(
                exchange=exchange,
                role="user",
                content=exchange.message_text,
            )
            return
        if not exchange.session_persisted:
            exchange.user_message_persistence_error = "chat_session_not_persisted"
            self.persist_redis_context_message(
                exchange=exchange,
                role="user",
                content=exchange.message_text,
            )
            return

        message_id = self.build_message_id()
        try:
            self.storage_bundle.chat_message_repository.append_message(
                ChatMessageRecord(
                    message_id=message_id,
                    session_id=exchange.effective_session_id,
                    sender_type="user",
                    message_text=exchange.message_text,
                )
            )
            exchange.user_message_id = message_id
            exchange.user_message_persisted = True
        except Exception:
            exchange.user_message_persisted = False
            exchange.user_message_persistence_error = "user_message_write_failed"
        self.persist_redis_context_message(
            exchange=exchange,
            role="user",
            content=exchange.message_text,
        )

    def append_assistant_message(
        self,
        exchange: ChatPersistenceExchange,
        agent_response: AgentResponse,
    ) -> None:
        self.record_stage(exchange, "append_assistant_message")
        if exchange.effective_session_id is None:
            exchange.assistant_message_persistence_error = "chat_session_missing"
            self.persist_redis_context_message(
                exchange=exchange,
                role="assistant",
                content=agent_response.reply_text,
            )
            return
        if not exchange.session_persisted:
            exchange.assistant_message_persistence_error = "chat_session_not_persisted"
            self.persist_redis_context_message(
                exchange=exchange,
                role="assistant",
                content=agent_response.reply_text,
            )
            return

        message_id = self.build_message_id()
        try:
            self.storage_bundle.chat_message_repository.append_message(
                ChatMessageRecord(
                    message_id=message_id,
                    session_id=exchange.effective_session_id,
                    sender_type="assistant",
                    message_text=agent_response.reply_text,
                )
            )
            exchange.assistant_message_id = message_id
            exchange.assistant_message_persisted = True
        except Exception:
            exchange.assistant_message_persisted = False
            exchange.assistant_message_persistence_error = (
                "assistant_message_write_failed"
            )
        self.persist_redis_context_message(
            exchange=exchange,
            role="assistant",
            content=agent_response.reply_text,
        )

    def persist_redis_context_message(
        self,
        exchange: ChatPersistenceExchange,
        role: str,
        content: str,
    ) -> None:
        self.record_stage(exchange, f"persist_redis_{role}_message")
        if self.redis_chat_context_store is None:
            exchange.redis_context_persistence_error = "redis_context_store_unavailable"
            return

        redis_write_succeeded = self.redis_chat_context_store.append_message(
            session_id=exchange.effective_session_id,
            role=role,
            content=content,
        )
        if redis_write_succeeded:
            exchange.redis_context_persisted = True
            return
        exchange.redis_context_persistence_error = "redis_context_write_failed"

    def persist_tool_invocation_logs(
        self,
        exchange: ChatPersistenceExchange,
        agent_response: AgentResponse,
    ) -> None:
        self.record_stage(exchange, "persist_tool_invocation_logs")
        if not agent_response.tool_invocation_results:
            exchange.tool_logs_persisted = True
            return
        if not exchange.user_message_persisted:
            exchange.tool_logs_persistence_error = "tool_logs_skipped_missing_user_message"
            return

        try:
            for tool_invocation_result in agent_response.tool_invocation_results:
                self.storage_bundle.tool_call_log_repository.create_tool_call_log(
                    ToolCallLogRecord(
                        tool_call_id=self.build_message_id(),
                        session_id=exchange.effective_session_id,
                        message_id=exchange.user_message_id,
                        actor_user_id=None,
                        tool_namespace=tool_invocation_result.domain,
                        tool_name=tool_invocation_result.tool_name,
                        call_status=tool_invocation_result.invocation_status,
                        request_payload=tool_invocation_result.request_payload,
                        response_payload=tool_invocation_result.response_payload,
                        error_message=None,
                        latency_ms=None,
                    )
                )
            exchange.tool_logs_persisted = True
        except Exception:
            exchange.tool_logs_persisted = False
            exchange.tool_logs_persistence_error = "tool_logs_write_failed"

    def persist_audit_events(
        self,
        exchange: ChatPersistenceExchange,
        agent_response: AgentResponse,
    ) -> None:
        self.record_stage(exchange, "persist_audit_events")
        if not exchange.session_persisted:
            exchange.audit_events_persistence_error = "audit_events_skipped_missing_session"
            return

        try:
            self.storage_bundle.audit_event_repository.create_audit_event(
                AuditEventRecord(
                    event_id=self.build_message_id(),
                    actor_user_id=None,
                    event_type="chat_exchange_completed",
                    event_summary="Chat exchange completed with persisted artifacts.",
                    event_payload={
                        "session_id": exchange.effective_session_id,
                        "user_message_id": exchange.user_message_id,
                        "assistant_message_id": exchange.assistant_message_id,
                        "tool_names": list(agent_response.tool_names),
                        "tool_invocation_count": len(
                            agent_response.tool_invocation_results
                        ),
                        "planner_source": (
                            agent_response.planner_result.planner_source
                            if agent_response.planner_result is not None
                            else None
                        ),
                        "persistence_status": {
                            "session_persisted": exchange.session_persisted,
                            "user_message_persisted": exchange.user_message_persisted,
                            "assistant_message_persisted": exchange.assistant_message_persisted,
                            "tool_logs_persisted": exchange.tool_logs_persisted,
                            "operational_records_persisted": exchange.operational_records_persisted,
                            "redis_context_persisted": exchange.redis_context_persisted,
                        },
                        "persistence_errors": {
                            "session": exchange.session_persistence_error,
                            "user_message": exchange.user_message_persistence_error,
                            "assistant_message": exchange.assistant_message_persistence_error,
                            "tool_logs": exchange.tool_logs_persistence_error,
                            "operational_records": exchange.operational_records_persistence_error,
                            "redis_context": exchange.redis_context_persistence_error,
                        },
                        "write_order": list(exchange.write_order),
                    },
                )
            )
            exchange.audit_events_persisted = True
        except Exception:
            exchange.audit_events_persisted = False
            exchange.audit_events_persistence_error = "audit_events_write_failed"

    def persist_operational_records(
        self,
        exchange: ChatPersistenceExchange,
        agent_response: AgentResponse,
    ) -> None:
        self.record_stage(exchange, "persist_operational_records")
        ops_results = [
            tool_invocation_result
            for tool_invocation_result in agent_response.tool_invocation_results
            if tool_invocation_result.tool_name == "ops.create_alert_or_action"
        ]
        if not ops_results:
            exchange.operational_records_persisted = True
            return
        if not exchange.assistant_message_persisted:
            exchange.operational_records_persistence_error = (
                "operational_records_skipped_missing_assistant_message"
            )
            return

        try:
            for ops_result in ops_results:
                recommended_action = ops_result.response_payload.get("recommended_action")
                if not isinstance(recommended_action, dict):
                    continue

                action_type = str(recommended_action.get("action_type", "action"))
                severity = str(recommended_action.get("severity", "medium"))
                summary = str(
                    recommended_action.get(
                        "summary_template",
                        "Operational action created from chat workflow.",
                    )
                )
                self.storage_bundle.risk_alert_repository.create_risk_alert(
                    RiskAlertRecord(
                        alert_id=self.build_message_id(),
                        session_id=exchange.effective_session_id,
                        message_id=exchange.assistant_message_id,
                        actor_user_id=None,
                        alert_type=action_type,
                        severity=severity,
                        status="open",
                        summary=summary,
                        details={
                            "tool_name": ops_result.tool_name,
                            "request_payload": ops_result.request_payload,
                            "recommended_action": recommended_action,
                            "templates": ops_result.response_payload.get("templates", []),
                        },
                    )
                )
            exchange.operational_records_persisted = True
        except Exception:
            exchange.operational_records_persisted = False
            exchange.operational_records_persistence_error = (
                "operational_records_write_failed"
            )

    def start_exchange(
        self,
        command: ChatCommand,
        normalized_role: str,
        normalized_text: str,
    ) -> ChatPersistenceExchange:
        exchange = ChatPersistenceExchange(
            user_role=command.user_role,
            normalized_role=normalized_role,
            message_text=command.message_text,
            normalized_text=normalized_text,
            requested_session_id=command.session_id,
            effective_session_id=self.build_session_id(command.session_id),
            recent_messages=list(command.recent_messages),
        )
        self.ensure_chat_session(exchange)
        self.append_user_message(exchange)
        return exchange

    def finish_exchange(
        self,
        exchange: ChatPersistenceExchange,
        agent_response: AgentResponse,
    ) -> ChatPersistenceResult:
        self.append_assistant_message(exchange, agent_response)
        self.persist_tool_invocation_logs(exchange, agent_response)
        self.persist_operational_records(exchange, agent_response)
        self.persist_audit_events(exchange, agent_response)
        return ChatPersistenceResult(
            session_persisted=exchange.session_persisted,
            session_persistence_error=exchange.session_persistence_error,
            user_message_persisted=exchange.user_message_persisted,
            user_message_persistence_error=exchange.user_message_persistence_error,
            assistant_message_persisted=exchange.assistant_message_persisted,
            assistant_message_persistence_error=exchange.assistant_message_persistence_error,
            tool_logs_persisted=exchange.tool_logs_persisted,
            tool_logs_persistence_error=exchange.tool_logs_persistence_error,
            audit_events_persisted=exchange.audit_events_persisted,
            audit_events_persistence_error=exchange.audit_events_persistence_error,
            operational_records_persisted=exchange.operational_records_persisted,
            operational_records_persistence_error=exchange.operational_records_persistence_error,
            redis_context_persisted=exchange.redis_context_persisted,
            redis_context_persistence_error=exchange.redis_context_persistence_error,
            write_order=list(exchange.write_order),
        )
