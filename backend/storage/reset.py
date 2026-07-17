from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from backend.storage.db import DatabaseClient, SQLStatement


class ResetScope(str, Enum):
    RUNTIME = "runtime"
    DEMO = "demo"


class ResetSafetyError(ValueError):
    """Raised when a reset target is outside the supported local boundary."""


RUNTIME_RESET_TABLES = (
    "risk.risk_alert_approvals",
    "risk.risk_alert_status_events",
    "risk.risk_alerts",
    "risk.batch_score_results",
    "risk.batch_score_runs",
    "audit.tool_call_logs",
    "audit.audit_events",
    "convo.chat_messages",
    "convo.chat_sessions",
    "iam.auth_sessions",
    "iam.api_tokens",
    "knowledge.ingestion_run_sources",
    "knowledge.ingestion_runs",
)

DEMO_RESET_TABLES = (
    "knowledge.chunk_embeddings",
    "knowledge.knowledge_chunks",
    "knowledge.knowledge_documents",
    "iam.user_credentials",
    "iam.user_role_bindings",
    "iam.users",
    "iam.roles",
)


@dataclass(frozen=True, slots=True)
class LocalResetTarget:
    """Describes the only database and Redis targets allowed by local reset."""

    app_env: str
    database_url: str
    redis_url: str
    allowed_database_names: tuple[str, ...] = ("mcp_gateway_agents",)
    allowed_database_hosts: tuple[str, ...] = (
        "127.0.0.1",
        "localhost",
        "postgres",
    )
    allowed_redis_hosts: tuple[str, ...] = (
        "127.0.0.1",
        "localhost",
        "redis",
    )

    def validate(self) -> None:
        if self.app_env.strip().lower() != "local":
            raise ResetSafetyError("Local reset requires APP_ENV=local.")

        database = urlparse(self.database_url)
        database_name = database.path.lstrip("/")
        database_host = database.hostname or ""
        if database.scheme not in {"postgres", "postgresql"}:
            raise ResetSafetyError("Local reset requires a PostgreSQL database URL.")
        if database_name not in self.allowed_database_names:
            raise ResetSafetyError(
                "Database name is not in the local reset allowlist."
            )
        if database_host not in self.allowed_database_hosts:
            raise ResetSafetyError(
                "Database host is not in the local reset allowlist."
            )

        redis = urlparse(self.redis_url)
        redis_host = redis.hostname or ""
        if redis.scheme not in {"redis", "rediss"}:
            raise ResetSafetyError("Local reset requires a Redis URL.")
        if redis_host not in self.allowed_redis_hosts:
            raise ResetSafetyError("Redis host is not in the local reset allowlist.")

    def redacted_payload(self) -> dict[str, object]:
        database = urlparse(self.database_url)
        redis = urlparse(self.redis_url)
        return {
            "app_env": self.app_env,
            "database_host": database.hostname,
            "database_name": database.path.lstrip("/"),
            "redis_host": redis.hostname,
            "redis_database": redis.path.lstrip("/") or "0",
        }


@dataclass(frozen=True, slots=True)
class LocalResetPlan:
    scope: ResetScope
    database_tables: tuple[str, ...]
    redis_key_prefixes: tuple[str, ...]
    release_seed_ledger: bool

    def to_payload(self) -> dict[str, object]:
        return {
            "scope": self.scope.value,
            "database_tables": list(self.database_tables),
            "redis_key_prefixes": list(self.redis_key_prefixes),
            "release_seed_ledger": self.release_seed_ledger,
        }


@dataclass(frozen=True, slots=True)
class LocalResetReport:
    scope: ResetScope
    database_rows_cleared: dict[str, int]
    seed_ledger_rows_released: int
    redis_keys_deleted: int
    redis_error: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "scope": self.scope.value,
            "database_rows_cleared": dict(self.database_rows_cleared),
            "seed_ledger_rows_released": self.seed_ledger_rows_released,
            "redis_keys_deleted": self.redis_keys_deleted,
            "redis_error": self.redis_error,
        }


def build_local_reset_plan(
    scope: ResetScope,
    response_cache_key_prefix: str,
) -> LocalResetPlan:
    normalized_prefix = response_cache_key_prefix.strip()
    if not normalized_prefix:
        raise ValueError("Response cache key prefix cannot be empty.")
    tables = RUNTIME_RESET_TABLES
    if scope is ResetScope.DEMO:
        tables = tables + DEMO_RESET_TABLES
    return LocalResetPlan(
        scope=scope,
        database_tables=tables,
        redis_key_prefixes=("chat:context", normalized_prefix),
        release_seed_ledger=scope is ResetScope.DEMO,
    )


class RedisScopedReset:
    """Delete only project-owned Redis keys under explicitly supplied prefixes."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url

    def _get_client(self):
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis is required for local reset runtime.") from exc
        return redis.Redis.from_url(self.redis_url, decode_responses=True)

    @staticmethod
    def _close_client(client) -> None:
        close = getattr(client, "close", None)
        if callable(close):
            close()

    def delete_key_prefixes(self, prefixes: tuple[str, ...]) -> int:
        client = self._get_client()
        deleted_count = 0
        try:
            for prefix in prefixes:
                keys = list(client.scan_iter(match=f"{prefix}:*"))
                if not keys:
                    continue
                client.delete(*keys)
                deleted_count += len(keys)
        finally:
            self._close_client(client)
        return deleted_count


@dataclass(slots=True)
class LocalResetService:
    database_client: DatabaseClient
    redis_reset: RedisScopedReset

    def execute(self, plan: LocalResetPlan) -> LocalResetReport:
        database_rows_cleared: dict[str, int] = {}
        seed_ledger_rows_released = 0
        with self.database_client.transaction() as transaction:
            for table_name in plan.database_tables:
                count_rows = transaction.fetch_all(
                    SQLStatement(
                        sql=f"SELECT COUNT(*) AS row_count FROM {table_name}",
                        params={},
                    )
                )
                database_rows_cleared[table_name] = int(
                    count_rows[0]["row_count"] if count_rows else 0
                )
                transaction.execute(
                    SQLStatement(
                        sql=f"TRUNCATE TABLE {table_name} RESTART IDENTITY",
                        params={},
                    )
                )

            if plan.release_seed_ledger:
                seed_rows = transaction.fetch_all(
                    SQLStatement(
                        sql=(
                            "SELECT COUNT(*) AS row_count "
                            "FROM public.local_sql_scripts "
                            "WHERE script_type = 'seed'"
                        ),
                        params={},
                    )
                )
                seed_ledger_rows_released = int(
                    seed_rows[0]["row_count"] if seed_rows else 0
                )
                transaction.execute(
                    SQLStatement(
                        sql=(
                            "DELETE FROM public.local_sql_scripts "
                            "WHERE script_type = 'seed'"
                        ),
                        params={},
                    )
                )

        redis_keys_deleted = 0
        redis_error: str | None = None
        try:
            redis_keys_deleted = self.redis_reset.delete_key_prefixes(
                plan.redis_key_prefixes
            )
        except Exception as exc:
            redis_error = type(exc).__name__
        return LocalResetReport(
            scope=plan.scope,
            database_rows_cleared=database_rows_cleared,
            seed_ledger_rows_released=seed_ledger_rows_released,
            redis_keys_deleted=redis_keys_deleted,
            redis_error=redis_error,
        )
