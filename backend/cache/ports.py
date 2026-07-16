from typing import Protocol

from backend.cache.contracts import CacheEntry, CacheReadResult, CacheWriteResult


class ResponseCachePort(Protocol):
    """Minimal adapter boundary for future Redis or test cache implementations."""

    def get(self, cache_key: str) -> CacheReadResult: ...

    def set(self, entry: CacheEntry) -> CacheWriteResult: ...

    def delete(self, cache_key: str) -> bool: ...
