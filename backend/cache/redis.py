import json
from dataclasses import dataclass
from typing import Any

from backend.cache.contracts import (
    CacheEntry,
    CacheReadResult,
    CacheStatus,
    CacheWriteResult,
)


@dataclass(slots=True)
class RedisResponseCache:
    """Redis adapter for the provider-neutral response-cache port."""

    redis_url: str

    def _import_redis(self) -> Any:
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis is required for response-cache runtime.") from exc
        return redis

    def _get_client(self) -> Any:
        redis = self._import_redis()
        return redis.Redis.from_url(self.redis_url, decode_responses=True)

    @staticmethod
    def _close_client(client: Any) -> None:
        close = getattr(client, "close", None)
        if callable(close):
            close()

    def get(self, cache_key: str) -> CacheReadResult:
        client = None
        try:
            client = self._get_client()
            raw_entry = client.get(cache_key)
        except Exception as exc:
            return CacheReadResult(
                status=CacheStatus.UNAVAILABLE,
                reason=type(exc).__name__,
            )
        finally:
            if client is not None:
                self._close_client(client)

        if raw_entry is None:
            return CacheReadResult(status=CacheStatus.MISS)

        try:
            payload = json.loads(raw_entry)
            entry = CacheEntry(
                cache_key=str(payload["cache_key"]),
                response_payload=dict(payload["response_payload"]),
                ttl_seconds=int(payload["ttl_seconds"]),
                created_at_epoch=float(payload["created_at_epoch"]),
            )
            if entry.cache_key != cache_key or entry.ttl_seconds <= 0:
                raise ValueError("Cache entry metadata is invalid.")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return CacheReadResult(
                status=CacheStatus.MISS,
                reason="invalid_entry",
            )

        return CacheReadResult(status=CacheStatus.HIT, entry=entry)

    def set(self, entry: CacheEntry) -> CacheWriteResult:
        client = None
        try:
            client = self._get_client()
            client.setex(
                entry.cache_key,
                entry.ttl_seconds,
                json.dumps(entry.to_payload(), ensure_ascii=True, sort_keys=True),
            )
        except Exception as exc:
            return CacheWriteResult(
                status=CacheStatus.UNAVAILABLE,
                reason=type(exc).__name__,
            )
        finally:
            if client is not None:
                self._close_client(client)
        return CacheWriteResult(status=CacheStatus.STORED)

    def delete(self, cache_key: str) -> bool:
        client = None
        try:
            client = self._get_client()
            client.delete(cache_key)
            return True
        except Exception:
            return False
        finally:
            if client is not None:
                self._close_client(client)
