import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.models import AgentResponse, ChatCommand, ChatHistoryMessage
from backend.storage.chat_persistence import (
    ChatPersistenceCoordinator,
    ChatPersistenceResult,
)
from backend.storage.db import SQLStatement
from backend.storage.models import ChatSessionRecord


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


class FailingChatSessionRepository:
    def create_session(self, record: ChatSessionRecord) -> SQLStatement:
        _ = record
        raise RuntimeError("db unavailable")


class FailingStorageBundle:
    def __init__(self) -> None:
        self.chat_session_repository = FailingChatSessionRepository()


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


def test_chat_persistence_coordinator_finishes_exchange_with_noop_result() -> None:
    coordinator = ChatPersistenceCoordinator(storage_bundle=FakeStorageBundle())
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

    assert result == ChatPersistenceResult(session_persisted=True)


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
    assert result == ChatPersistenceResult(
        session_persisted=False,
        session_persistence_error="chat_session_write_failed",
    )
