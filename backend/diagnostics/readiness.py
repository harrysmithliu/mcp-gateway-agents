from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from backend.diagnostics.contracts import (
    ReadinessComponent,
    ReadinessReason,
    ReadinessState,
    RuntimeReadinessReport,
)
from backend.retrieval.service import RetrievalService
from backend.storage.db import DatabaseClient
from backend.storage.redis_chat_context import RedisChatContextStore
from backend.storage.settings import Settings


def _dependency_failure(exc: Exception) -> tuple[ReadinessReason, str]:
    error_name = type(exc).__name__.lower()
    if isinstance(exc, TimeoutError) or "timeout" in error_name:
        return (
            ReadinessReason.DEPENDENCY_TIMEOUT,
            "The dependency did not respond within the configured timeout.",
        )
    return (
        ReadinessReason.DEPENDENCY_UNAVAILABLE,
        "The dependency could not be reached or accepted the connection.",
    )


def _redacted_url_summary(raw_url: str) -> dict[str, object]:
    parsed = urlparse(raw_url)
    database = parsed.path.lstrip("/") or None
    return {
        "scheme": parsed.scheme or "unknown",
        "host": parsed.hostname or "unknown",
        "port": parsed.port,
        "database": database,
        "configured": bool(raw_url),
    }


def _component_state(raw_state: str) -> ReadinessState:
    try:
        return ReadinessState(raw_state)
    except ValueError:
        return ReadinessState.UNAVAILABLE


@dataclass(slots=True)
class RuntimeReadinessService:
    """Runs read-only checks against already-built application dependencies."""

    settings: Settings
    database_client: DatabaseClient
    redis_chat_context_store: RedisChatContextStore
    retrieval_service: RetrievalService
    response_cache_enabled: bool
    response_cache_ttl_seconds: int
    response_cache_key_prefix: str
    tool_registry: Any

    def check(self) -> RuntimeReadinessReport:
        postgres = self._check_postgres()
        redis = self._check_redis()
        retrieval = self._check_retrieval()
        cache = self._check_cache(redis)
        mcp = self._check_mcp()
        backend = ReadinessComponent(
            name="backend",
            state=ReadinessState.READY,
            reason_code=ReadinessReason.CONFIGURED,
            message="Backend application container is initialized.",
        )
        components = (backend, postgres, redis, retrieval, cache, mcp)
        return RuntimeReadinessReport(
            state=self._overall_state(components),
            components=components,
            config=self._config_summary(),
        )

    def _check_postgres(self) -> ReadinessComponent:
        try:
            with self.database_client.connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
        except Exception as exc:
            reason_code, message = _dependency_failure(exc)
            return ReadinessComponent(
                name="postgresql",
                state=ReadinessState.UNAVAILABLE,
                reason_code=reason_code,
                message=message,
                remediation="Start the PostgreSQL/pgvector service and verify DATABASE_URL.",
            )
        return ReadinessComponent(
            name="postgresql",
            state=ReadinessState.READY,
            reason_code=ReadinessReason.CONFIGURED,
            message="PostgreSQL accepted a read-only connectivity check.",
            details={"vector_backend": "pgvector"},
        )

    def _check_redis(self) -> ReadinessComponent:
        client = None
        try:
            client = self.redis_chat_context_store._get_client()
            client.ping()
        except Exception as exc:
            reason_code, message = _dependency_failure(exc)
            return ReadinessComponent(
                name="redis",
                state=ReadinessState.UNAVAILABLE,
                reason_code=reason_code,
                message=message,
                remediation="Start Redis and verify REDIS_URL.",
            )
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        return ReadinessComponent(
            name="redis",
            state=ReadinessState.READY,
            reason_code=ReadinessReason.CONFIGURED,
            message="Redis accepted a read-only ping.",
        )

    def _check_retrieval(self) -> ReadinessComponent:
        status = self.retrieval_service.runtime_status()
        state = _component_state(status.state)
        reason_code = ReadinessReason.CONFIGURED
        if state == ReadinessState.DISABLED:
            reason_code = ReadinessReason.DISABLED_BY_CONFIGURATION
        elif state == ReadinessState.UNAVAILABLE:
            reason_code = ReadinessReason.INITIALIZATION_FAILED
        return ReadinessComponent(
            name="retrieval",
            state=state,
            reason_code=reason_code,
            message=(
                "Knowledge retrieval runtime is configured."
                if state == ReadinessState.READY
                else "Knowledge retrieval runtime is not ready."
            ),
            remediation=(
                "Verify retrieval and embedding configuration."
                if state != ReadinessState.READY
                else None
            ),
            details={
                "enabled": status.enabled,
                "vector_backend": status.vector_backend,
                "provider": status.provider,
                "model_name": status.model_name,
                "vector_dimensions": status.vector_dimensions,
                "reason": status.reason,
            },
        )

    def _check_cache(self, redis: ReadinessComponent) -> ReadinessComponent:
        if not self.response_cache_enabled:
            return ReadinessComponent(
                name="response_cache",
                state=ReadinessState.DISABLED,
                reason_code=ReadinessReason.DISABLED_BY_CONFIGURATION,
                message="Response cache is disabled by configuration.",
                details={"key_prefix": self.response_cache_key_prefix},
            )
        state = (
            ReadinessState.READY
            if redis.state == ReadinessState.READY
            else ReadinessState.DEGRADED
        )
        return ReadinessComponent(
            name="response_cache",
            state=state,
            reason_code=(
                ReadinessReason.CONFIGURED
                if state == ReadinessState.READY
                else ReadinessReason.DEPENDENCY_UNAVAILABLE
            ),
            message=(
                "Response cache is configured on the available Redis runtime."
                if state == ReadinessState.READY
                else "Response cache is configured but Redis is unavailable."
            ),
            remediation=(
                None
                if state == ReadinessState.READY
                else "Restore Redis connectivity before relying on response caching."
            ),
            details={
                "ttl_seconds": self.response_cache_ttl_seconds,
                "key_prefix": self.response_cache_key_prefix,
            },
        )

    def _check_mcp(self) -> ReadinessComponent:
        try:
            tool_names = tuple(self.tool_registry.list_tool_names())
        except Exception:
            return ReadinessComponent(
                name="mcp",
                state=ReadinessState.UNAVAILABLE,
                reason_code=ReadinessReason.INITIALIZATION_FAILED,
                message="MCP tool registry could not be inspected.",
                remediation="Verify MCP registry and transport configuration.",
            )
        return ReadinessComponent(
            name="mcp",
            state=ReadinessState.READY,
            reason_code=ReadinessReason.CONFIGURED,
            message="MCP tool registry is available for inspection.",
            details={
                "transport_mode": self.settings.mcp_transport_mode,
                "server_runtime": self.settings.mcp_server_runtime,
                "tool_count": len(tool_names),
                "tool_names": tool_names,
            },
        )

    def _config_summary(self) -> dict[str, object]:
        return {
            "app_env": self.settings.app_env,
            "database": _redacted_url_summary(self.settings.database_url),
            "redis": _redacted_url_summary(self.settings.redis_url),
            "retrieval_enabled": self.settings.retrieval_enabled,
            "embedding_provider": self.settings.embedding_provider,
            "embedding_model_name": self.settings.embedding_model_name,
            "embedding_dimensions": self.settings.embedding_dimensions,
            "mcp_transport_mode": self.settings.mcp_transport_mode,
            "mcp_server_runtime": self.settings.mcp_server_runtime,
        }

    @staticmethod
    def _overall_state(
        components: tuple[ReadinessComponent, ...],
    ) -> ReadinessState:
        if any(
            component.name in {"postgresql", "redis", "backend"}
            and component.state == ReadinessState.UNAVAILABLE
            for component in components
        ):
            return ReadinessState.UNAVAILABLE
        if any(
            component.state
            in {ReadinessState.DEGRADED, ReadinessState.UNAVAILABLE}
            for component in components
        ):
            return ReadinessState.DEGRADED
        if any(
            component.state == ReadinessState.DISABLED
            and component.name != "response_cache"
            for component in components
        ):
            return ReadinessState.DEGRADED
        return ReadinessState.READY
