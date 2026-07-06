import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.models import ChatHistoryMessage
from backend.storage.redis_chat_context import RedisChatContextStore


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, list[str]] = {}

    def rpush(self, key: str, value: str) -> None:
        self.values.setdefault(key, []).append(value)

    def ltrim(self, key: str, start: int, end: int) -> None:
        values = self.values.get(key, [])
        if not values:
            return
        normalized_start = len(values) + start if start < 0 else start
        normalized_end = len(values) + end if end < 0 else end
        normalized_start = max(normalized_start, 0)
        normalized_end = min(normalized_end, len(values) - 1)
        self.values[key] = values[normalized_start : normalized_end + 1]

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self.values.get(key, [])
        if end == -1:
            end = len(values) - 1
        return values[start : end + 1]


class FakeRedisChatContextStore(RedisChatContextStore):
    __slots__ = ("_fake_client",)

    def __init__(
        self,
        fake_client: FakeRedisClient,
        redis_url: str,
        max_messages: int,
    ) -> None:
        super().__init__(redis_url=redis_url, max_messages=max_messages)
        self._fake_client = fake_client

    def _get_client(self) -> FakeRedisClient:
        return self._fake_client


def test_redis_chat_context_store_appends_and_loads_recent_messages() -> None:
    fake_client = FakeRedisClient()
    store = FakeRedisChatContextStore(
        fake_client=fake_client,
        redis_url="redis://example",
        max_messages=3,
    )

    assert store.append_message("session-r7-001", "user", "first") is True
    assert store.append_message("session-r7-001", "assistant", "second") is True
    assert store.append_message("session-r7-001", "user", "third") is True
    assert store.append_message("session-r7-001", "assistant", "fourth") is True

    recent_messages = store.load_recent_messages("session-r7-001")

    assert recent_messages == [
        ChatHistoryMessage(role="assistant", content="second"),
        ChatHistoryMessage(role="user", content="third"),
        ChatHistoryMessage(role="assistant", content="fourth"),
    ]


def test_redis_chat_context_store_returns_empty_messages_when_session_missing() -> None:
    fake_client = FakeRedisClient()
    store = FakeRedisChatContextStore(
        fake_client=fake_client,
        redis_url="redis://example",
        max_messages=3,
    )

    assert store.load_recent_messages(None) == []
    assert store.append_message(None, "user", "ignored") is False
