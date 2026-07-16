"""Provider-neutral response-cache contracts and eligibility policy."""

from backend.cache.contracts import (
    CacheBypassReason,
    CacheDecision,
    CacheEntry,
    CacheEligibility,
    CacheReadResult,
    CacheRequestContext,
    CacheStatus,
    CacheWriteResult,
)
from backend.cache.keys import build_cache_key, build_history_fingerprint
from backend.cache.policy import CacheEligibilityPolicy
from backend.cache.ports import ResponseCachePort

__all__ = [
    "CacheBypassReason",
    "CacheDecision",
    "CacheEntry",
    "CacheEligibility",
    "CacheReadResult",
    "CacheEligibilityPolicy",
    "CacheRequestContext",
    "ResponseCachePort",
    "CacheStatus",
    "CacheWriteResult",
    "build_cache_key",
    "build_history_fingerprint",
]
