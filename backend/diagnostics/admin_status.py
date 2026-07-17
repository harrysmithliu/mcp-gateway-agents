from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.diagnostics.contracts import (
    AdminRuntimeStatusReport,
)
from backend.diagnostics.readiness import RuntimeReadinessService
from backend.mcp_gateway.sdk_adapter import MCPSDKAdapter
from backend.storage.bootstrap import build_local_sql_plan
from backend.storage.db import DatabaseClient
from backend.storage.settings import Settings


@dataclass(slots=True)
class AdminRuntimeStatusService:
    """Aggregates read-only, operator-safe runtime status for the admin surface."""

    settings: Settings
    database_client: DatabaseClient
    readiness_service: RuntimeReadinessService
    mcp_sdk_adapter: MCPSDKAdapter
    project_root: Path

    def build_report(self) -> AdminRuntimeStatusReport:
        readiness = self.readiness_service.check()
        return AdminRuntimeStatusReport(
            observed_at=datetime.now(timezone.utc),
            environment=self.settings.app_env,
            readiness=readiness,
            runtime_mode=self._runtime_mode(),
            migration=self._migration_status(),
            mcp=self._mcp_status(),
        )

    def _runtime_mode(self) -> dict[str, object]:
        return {
            "app_name": self.settings.app_name,
            "app_env": self.settings.app_env,
            "auth_mode": self.settings.auth_mode,
            "retrieval_enabled": self.settings.retrieval_enabled,
            "embedding_provider": self.settings.embedding_provider,
            "embedding_model_name": self.settings.embedding_model_name,
            "embedding_dimensions": self.settings.embedding_dimensions,
            "response_cache_enabled": self.settings.response_cache_enabled,
            "mcp_transport_mode": self.settings.mcp_transport_mode,
            "mcp_server_runtime": self.settings.mcp_server_runtime,
        }

    def _mcp_status(self) -> dict[str, object]:
        status = self.mcp_sdk_adapter.build_sdk_status()
        visible_fields = (
            "package_available",
            "sdk_version",
            "sdk_stable_line",
            "transport_mode",
            "server_runtime",
            "sdk_tool_names",
            "integration_mode",
            "recommended_next_step",
        )
        return {field: status[field] for field in visible_fields if field in status}

    def _migration_status(self) -> dict[str, object]:
        expected_count = len(build_local_sql_plan(self.project_root).migrations)
        try:
            with self.database_client.connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM public.local_sql_scripts
                        WHERE script_type = 'migration'
                        """
                    )
                    row = cursor.fetchone()
            applied_count = int(row[0]) if row is not None else 0
        except Exception:
            return {
                "state": "unavailable",
                "expected_count": expected_count,
                "applied_count": None,
                "reason": "migration_status_check_failed",
            }

        if applied_count < expected_count:
            return {
                "state": "degraded",
                "expected_count": expected_count,
                "applied_count": applied_count,
                "reason": "migration_scripts_pending",
            }
        return {
            "state": "ready",
            "expected_count": expected_count,
            "applied_count": applied_count,
            "reason": "migration_scripts_applied",
        }
