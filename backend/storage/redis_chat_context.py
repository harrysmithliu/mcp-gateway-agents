import json
from dataclasses import dataclass
from typing import Any

from backend.agent.models import ChatHistoryMessage


@dataclass(frozen=True, slots=True)
class RedisChatContextLoad:
    """Result envelope that distinguishes an empty key from Redis failure."""

    messages: list[ChatHistoryMessage]
    available: bool


@dataclass(slots=True)
class RedisChatContextStore:
    """Minimal Redis-backed short-term chat context store."""

    redis_url: str
    key_prefix: str = "chat:context"
    max_messages: int = 6

    def _import_redis(self) -> Any:
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis is required for Redis chat context runtime.") from exc
        return redis

    def _get_client(self) -> Any:
        redis = self._import_redis()
        return redis.Redis.from_url(self.redis_url, decode_responses=True)

    def _build_key(self, session_id: str, user_id: int | None = None) -> str:
        if user_id is None:
            return f"{self.key_prefix}:{session_id}"
        return f"{self.key_prefix}:user:{user_id}:{session_id}"

    def load_recent_messages(
        self,
        session_id: str | None,
        limit: int | None = None,
        user_id: int | None = None,
    ) -> list[ChatHistoryMessage]:
        return self.load_recent_messages_with_status(
            session_id=session_id,
            limit=limit,
            user_id=user_id,
        ).messages

    def load_recent_messages_with_status(
        self,
        session_id: str | None,
        limit: int | None = None,
        user_id: int | None = None,
    ) -> RedisChatContextLoad:
        if not session_id:
            return RedisChatContextLoad(messages=[], available=True)

        try:
            client = self._get_client()
            raw_messages = client.lrange(self._build_key(session_id, user_id), 0, -1)
        except Exception:
            return RedisChatContextLoad(messages=[], available=False)

        recent_messages: list[ChatHistoryMessage] = []
        for raw_message in raw_messages:
            try:
                payload = json.loads(raw_message)
                recent_messages.append(
                    ChatHistoryMessage(
                        role=str(payload["role"]),
                        content=str(payload["content"]),
                    )
                )
            except Exception:
                continue

        if limit is None:
            return RedisChatContextLoad(messages=recent_messages, available=True)
        return RedisChatContextLoad(
            messages=recent_messages[-limit:],
            available=True,
        )

    def append_message(
        self,
        session_id: str | None,
        role: str,
        content: str,
        user_id: int | None = None,
    ) -> bool:
        if not session_id:
            return False

        try:
            client = self._get_client()
            key = self._build_key(session_id, user_id)
            client.rpush(
                key,
                json.dumps(
                    {
                        "role": role,
                        "content": content,
                    }
                ),
            )
            client.ltrim(key, -self.max_messages, -1)
            return True
        except Exception:
            return False
