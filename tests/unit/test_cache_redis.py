from dataclasses import dataclass, field

from backend.cache.contracts import CacheEntry, CacheStatus
from backend.cache.redis import RedisResponseCache


@dataclass
class FakeRedisClient:
    values: dict[str, str] = field(default_factory=dict)
    fail_reads: bool = False
    fail_writes: bool = False

    def get(self, key: str) -> str | None:
        if self.fail_reads:
            raise RuntimeError("redis read failed")
        return self.values.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        if self.fail_writes:
            raise RuntimeError("redis write failed")
        self.values[key] = value

    def delete(self, key: str) -> None:
        self.values.pop(key, None)

    def close(self) -> None:
        return None


def build_cache_entry() -> CacheEntry:
    return CacheEntry(
        cache_key="agent:response:v1:test-key",
        response_payload={"reply_text": "cached response"},
        ttl_seconds=120,
    )


class FakeRedisResponseCache(RedisResponseCache):
    def __init__(self, client: FakeRedisClient) -> None:
        super().__init__(redis_url="redis://unused")
        self.client = client

    def _get_client(self) -> FakeRedisClient:
        return self.client


def test_redis_response_cache_round_trips_entry() -> None:
    client = FakeRedisClient()
    cache = FakeRedisResponseCache(client)

    write_result = cache.set(build_cache_entry())
    read_result = cache.get("agent:response:v1:test-key")

    assert write_result.status is CacheStatus.STORED
    assert read_result.status is CacheStatus.HIT
    assert read_result.entry is not None
    assert read_result.entry.response_payload == {"reply_text": "cached response"}


def test_redis_response_cache_reports_miss_and_invalid_entry() -> None:
    client = FakeRedisClient(values={"bad": "{}"})
    cache = FakeRedisResponseCache(client)

    assert cache.get("missing").status is CacheStatus.MISS
    invalid_result = cache.get("bad")

    assert invalid_result.status is CacheStatus.MISS
    assert invalid_result.reason == "invalid_entry"


def test_redis_response_cache_reports_provider_failures() -> None:
    read_failure_client = FakeRedisClient(fail_reads=True)
    cache = FakeRedisResponseCache(read_failure_client)

    read_result = cache.get("any-key")
    assert read_result.status is CacheStatus.UNAVAILABLE
    assert read_result.reason == "RuntimeError"

    write_failure_client = FakeRedisClient(fail_writes=True)
    cache.client = write_failure_client
    write_result = cache.set(build_cache_entry())
    assert write_result.status is CacheStatus.UNAVAILABLE
    assert write_result.reason == "RuntimeError"
