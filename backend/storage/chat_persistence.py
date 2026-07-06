from dataclasses import dataclass, field
from uuid import uuid4

from backend.agent.models import AgentResponse, ChatCommand, ChatHistoryMessage
from backend.storage.models import ChatSessionRecord
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
    session_persisted: bool = False
    session_persistence_error: str | None = None
    recent_messages: list[ChatHistoryMessage] = field(default_factory=list)


@dataclass(slots=True)
class ChatPersistenceResult:
    """Progress marker for staged chat persistence rollout."""

    session_persisted: bool = False
    session_persistence_error: str | None = None
    user_message_persisted: bool = False
    assistant_message_persisted: bool = False
    tool_logs_persisted: bool = False
    audit_events_persisted: bool = False
    operational_records_persisted: bool = False


@dataclass(slots=True)
class ChatPersistenceCoordinator:
    """Single entrypoint for future chat persistence orchestration."""

    storage_bundle: StorageBundle

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

    def ensure_chat_session(
        self,
        exchange: ChatPersistenceExchange,
    ) -> None:
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
        return exchange

    def finish_exchange(
        self,
        exchange: ChatPersistenceExchange,
        agent_response: AgentResponse,
    ) -> ChatPersistenceResult:
        _ = exchange, agent_response, self.storage_bundle
        return ChatPersistenceResult(
            session_persisted=exchange.session_persisted,
            session_persistence_error=exchange.session_persistence_error,
        )
