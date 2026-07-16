from dataclasses import dataclass

import pytest

from backend.agent.models import ChatCommand, ChatHistoryMessage
from backend.storage.chat_persistence import (
    ChatPersistenceCoordinator,
    ChatSessionAccessError,
)
from backend.storage.redis_chat_context import RedisChatContextLoad


class FakeSessionRepository:
    def __init__(self, session: dict[str, object] | None) -> None:
        self.session = session

    def get_session(self, session_id: str) -> dict[str, object] | None:
        return self.session


class FakeMessageRepository:
    def __init__(self, messages: list[ChatHistoryMessage]) -> None:
        self.messages = messages
        self.calls: list[tuple[str, int]] = []

    def list_recent_messages(
        self,
        session_id: str,
        limit: int = 6,
    ) -> list[ChatHistoryMessage]:
        self.calls.append((session_id, limit))
        return self.messages


class FakeRedisHistoryStore:
    def __init__(self, result: RedisChatContextLoad) -> None:
        self.result = result
        self.calls: list[tuple[str | None, int, int | None]] = []

    def load_recent_messages_with_status(
        self,
        session_id: str | None,
        limit: int | None = None,
        user_id: int | None = None,
    ) -> RedisChatContextLoad:
        self.calls.append((session_id, limit or 0, user_id))
        return self.result


@dataclass
class FakeStorageBundle:
    chat_session_repository: FakeSessionRepository
    chat_message_repository: FakeMessageRepository


def build_command(user_id: int = 7) -> ChatCommand:
    return ChatCommand(
        user_role="analyst",
        message_text="Use the previous context.",
        session_id="session-history-1",
        user_id=user_id,
        recent_messages=[
            ChatHistoryMessage(role="user", content="client supplied context")
        ],
    )


def build_coordinator(
    redis_result: RedisChatContextLoad,
    durable_messages: list[ChatHistoryMessage],
    session: dict[str, object] | None = None,
) -> tuple[ChatPersistenceCoordinator, FakeMessageRepository, FakeRedisHistoryStore]:
    message_repository = FakeMessageRepository(durable_messages)
    redis_store = FakeRedisHistoryStore(redis_result)
    coordinator = ChatPersistenceCoordinator(
        storage_bundle=FakeStorageBundle(
            chat_session_repository=FakeSessionRepository(
                session or {"session_id": "session-history-1", "user_id": 7}
            ),
            chat_message_repository=message_repository,
        ),
        redis_chat_context_store=redis_store,
    )
    return coordinator, message_repository, redis_store


def test_server_history_prefers_user_scoped_redis_context() -> None:
    redis_messages = [ChatHistoryMessage(role="assistant", content="Redis answer")]
    coordinator, message_repository, redis_store = build_coordinator(
        RedisChatContextLoad(messages=redis_messages, available=True),
        [ChatHistoryMessage(role="user", content="PostgreSQL answer")],
    )

    restored = coordinator.restore_recent_messages(build_command(), limit=4)

    assert restored.messages == redis_messages
    assert restored.source == "redis"
    assert restored.fallback_reason is None
    assert message_repository.calls == []
    assert redis_store.calls == [("session-history-1", 4, 7)]


def test_server_history_falls_back_to_postgres_when_redis_unavailable() -> None:
    durable_messages = [ChatHistoryMessage(role="user", content="Durable question")]
    coordinator, _, _ = build_coordinator(
        RedisChatContextLoad(messages=[], available=False),
        durable_messages,
    )

    restored = coordinator.restore_recent_messages(build_command())

    assert restored.messages == durable_messages
    assert restored.source == "postgresql"
    assert restored.fallback_reason == "redis_unavailable"


def test_server_history_rejects_cross_user_session() -> None:
    coordinator, _, _ = build_coordinator(
        RedisChatContextLoad(messages=[], available=True),
        [],
        session={"session_id": "session-history-1", "user_id": 99},
    )

    with pytest.raises(ChatSessionAccessError):
        coordinator.restore_recent_messages(build_command(user_id=7))


def test_server_history_ignores_client_messages_without_owned_session() -> None:
    coordinator, _, _ = build_coordinator(
        RedisChatContextLoad(messages=[], available=True),
        [],
        session=None,
    )
    command = build_command()
    command.session_id = None

    restored = coordinator.restore_recent_messages(command)

    assert restored.messages == []
    assert restored.source == "current_turn_only"
    assert restored.fallback_reason == "server_session_or_user_missing"
