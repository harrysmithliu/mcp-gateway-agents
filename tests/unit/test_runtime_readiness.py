from types import SimpleNamespace

from backend.diagnostics.contracts import ReadinessState
from backend.diagnostics.readiness import RuntimeReadinessService
from backend.retrieval.service import RetrievalService
from backend.storage.db import DatabaseClient, DatabaseConfig
from backend.storage.redis_chat_context import RedisChatContextStore
from backend.storage.settings import Settings


class FakeCursor:
    def execute(self, sql: str) -> None:
        assert sql == "SELECT 1"

    def fetchone(self) -> tuple[int]:
        return (1,)

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeConnection:
    def cursor(self) -> FakeCursor:
        return FakeCursor()

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeDatabaseClient(DatabaseClient):
    def __init__(self) -> None:
        super().__init__(DatabaseConfig(database_url="postgresql://user:secret@db:5432/app"))

    def connect(self):
        return FakeConnection()


class FakeRedisClient:
    def __init__(self) -> None:
        self.closed = False

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        self.closed = True


class FakeRedisStore(RedisChatContextStore):
    def __init__(self) -> None:
        super().__init__(redis_url="redis://:secret@redis:6379/0")
        self.client = FakeRedisClient()

    def _get_client(self) -> FakeRedisClient:
        return self.client


def build_service(
    *,
    retrieval_service: RetrievalService | None = None,
    response_cache_enabled: bool = False,
) -> RuntimeReadinessService:
    settings = Settings(
        database_url="postgresql://user:secret@db:5432/app",
        redis_url="redis://:secret@redis:6379/0",
        retrieval_enabled=False,
        mcp_transport_mode="registry",
    )
    registry = SimpleNamespace(list_tool_names=lambda: ["knowledge.search"])
    return RuntimeReadinessService(
        settings=settings,
        database_client=FakeDatabaseClient(),
        redis_chat_context_store=FakeRedisStore(),
        retrieval_service=retrieval_service or RetrievalService(enabled=False),
        response_cache_enabled=response_cache_enabled,
        response_cache_ttl_seconds=300,
        response_cache_key_prefix="agent:response",
        tool_registry=registry,
    )


def test_readiness_checks_dependencies_without_writing_or_loading_models() -> None:
    report = build_service().check()

    assert report.state == ReadinessState.DEGRADED
    states = {item.name: item.state for item in report.components}
    assert states["backend"] == ReadinessState.READY
    assert states["postgresql"] == ReadinessState.READY
    assert states["redis"] == ReadinessState.READY
    assert states["retrieval"] == ReadinessState.DISABLED
    assert states["response_cache"] == ReadinessState.DISABLED
    assert states["mcp"] == ReadinessState.READY
    assert report.config["database"] == {
        "scheme": "postgresql",
        "host": "db",
        "port": 5432,
        "database": "app",
        "configured": True,
    }
    assert "secret" not in str(report.to_payload())


def test_cache_degrades_when_redis_probe_fails() -> None:
    service = build_service(response_cache_enabled=True)
    service.redis_chat_context_store.client.ping = lambda: (_ for _ in ()).throw(
        ConnectionError("redis unavailable")
    )

    report = service.check()
    components = {item.name: item for item in report.components}

    assert report.state == ReadinessState.UNAVAILABLE
    assert components["redis"].state == ReadinessState.UNAVAILABLE
    assert components["response_cache"].state == ReadinessState.DEGRADED
    assert components["response_cache"].reason_code.value == "dependency_unavailable"
