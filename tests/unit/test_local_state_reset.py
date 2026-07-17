from contextlib import contextmanager

import pytest

from backend.storage.reset import (
    DEMO_RESET_TABLES,
    RUNTIME_RESET_TABLES,
    LocalResetService,
    LocalResetTarget,
    LocalResetPlan,
    RedisScopedReset,
    ResetSafetyError,
    ResetScope,
    build_local_reset_plan,
)


class FakeTransaction:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def fetch_all(self, statement) -> list[dict[str, int]]:
        if "local_sql_scripts" in statement.sql:
            return [{"row_count": 2}]
        return [{"row_count": 3}]

    def execute(self, statement) -> None:
        self.executed_sql.append(statement.sql)


class FakeDatabaseClient:
    def __init__(self) -> None:
        self.transaction_instance = FakeTransaction()

    @contextmanager
    def transaction(self):
        yield self.transaction_instance


class FakeRedisReset:
    def __init__(self) -> None:
        self.prefixes: tuple[str, ...] | None = None

    def delete_key_prefixes(self, prefixes: tuple[str, ...]) -> int:
        self.prefixes = prefixes
        return 4


def build_target(**overrides: str) -> LocalResetTarget:
    values = {
        "app_env": "local",
        "database_url": "postgresql://postgres:postgres@localhost:5432/mcp_gateway_agents",
        "redis_url": "redis://localhost:6379/0",
    }
    values.update(overrides)
    return LocalResetTarget(**values)


def test_reset_target_accepts_local_host_and_redacts_credentials() -> None:
    target = build_target()

    target.validate()

    payload = target.redacted_payload()
    assert payload == {
        "app_env": "local",
        "database_host": "localhost",
        "database_name": "mcp_gateway_agents",
        "redis_host": "localhost",
        "redis_database": "0",
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"app_env": "production"},
        {"database_url": "postgresql://postgres:postgres@remote:5432/mcp_gateway_agents"},
        {"database_url": "postgresql://postgres:postgres@localhost:5432/other"},
        {"redis_url": "redis://remote:6379/0"},
    ],
)
def test_reset_target_rejects_unsafe_targets(overrides: dict[str, str]) -> None:
    with pytest.raises(ResetSafetyError):
        build_target(**overrides).validate()


def test_runtime_plan_preserves_identity_and_knowledge() -> None:
    plan = build_local_reset_plan(ResetScope.RUNTIME, "agent:response")

    assert plan.database_tables == RUNTIME_RESET_TABLES
    assert plan.release_seed_ledger is False
    assert plan.redis_key_prefixes == ("chat:context", "agent:response")


def test_demo_plan_extends_runtime_with_identity_and_knowledge() -> None:
    plan = build_local_reset_plan(ResetScope.DEMO, "agent:response")

    assert plan.database_tables == RUNTIME_RESET_TABLES + DEMO_RESET_TABLES
    assert plan.release_seed_ledger is True


def test_reset_service_clears_allowlisted_rows_and_scoped_redis_keys() -> None:
    database = FakeDatabaseClient()
    redis_reset = FakeRedisReset()
    service = LocalResetService(database_client=database, redis_reset=redis_reset)

    report = service.execute(
        LocalResetPlan(
            scope=ResetScope.DEMO,
            database_tables=("risk.risk_alerts",),
            redis_key_prefixes=("chat:context", "agent:response"),
            release_seed_ledger=True,
        )
    )

    assert report.database_rows_cleared == {"risk.risk_alerts": 3}
    assert report.seed_ledger_rows_released == 2
    assert report.redis_keys_deleted == 4
    assert report.redis_error is None
    assert redis_reset.prefixes == ("chat:context", "agent:response")
    assert any("TRUNCATE TABLE risk.risk_alerts RESTART IDENTITY" in sql for sql in database.transaction_instance.executed_sql)
    assert all("CASCADE" not in sql for sql in database.transaction_instance.executed_sql)


def test_reset_service_reports_redis_failure_after_database_commit() -> None:
    class FailingRedisReset:
        def delete_key_prefixes(self, prefixes: tuple[str, ...]) -> int:
            raise RuntimeError("redis unavailable")

    report = LocalResetService(
        database_client=FakeDatabaseClient(),
        redis_reset=FailingRedisReset(),
    ).execute(
        LocalResetPlan(
            scope=ResetScope.RUNTIME,
            database_tables=("risk.risk_alerts",),
            redis_key_prefixes=("chat:context",),
            release_seed_ledger=False,
        )
    )

    assert report.database_rows_cleared == {"risk.risk_alerts": 3}
    assert report.redis_keys_deleted == 0
    assert report.redis_error == "RuntimeError"


def test_redis_reset_deletes_only_requested_prefixes() -> None:
    class FakeRedisClient:
        def __init__(self) -> None:
            self.keys = {
                "chat:context:user:2:session-1",
                "agent:response:v1:abc",
                "other:application:key",
            }
            self.deleted: list[str] = []

        def scan_iter(self, match: str):
            prefix = match.removesuffix("*")
            return (key for key in self.keys if key.startswith(prefix))

        def delete(self, *keys: str) -> None:
            self.deleted.extend(keys)
            self.keys.difference_update(keys)

        def close(self) -> None:
            return None

    fake_client = FakeRedisClient()

    class FakeRedisScopedReset(RedisScopedReset):
        def __init__(self) -> None:
            super().__init__(redis_url="redis://unused")

        def _get_client(self) -> FakeRedisClient:
            return fake_client

    reset = FakeRedisScopedReset()

    deleted_count = reset.delete_key_prefixes(("chat:context", "agent:response"))

    assert deleted_count == 2
    assert set(fake_client.deleted) == {
        "chat:context:user:2:session-1",
        "agent:response:v1:abc",
    }
    assert fake_client.keys == {"other:application:key"}
