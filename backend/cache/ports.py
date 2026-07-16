from typing import Protocol

from backend.cache.contracts import CacheEntry


class ResponseCachePort(Protocol):
    """Minimal adapter boundary for future Redis or test cache implementations."""

    def get(self, cache_key: str) -> CacheEntry | None: ...

    def set(self, entry: CacheEntry) -> bool: ...

    def delete(self, cache_key: str) -> bool: ...
