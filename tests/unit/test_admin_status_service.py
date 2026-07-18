from pathlib import Path
from types import SimpleNamespace

from backend.diagnostics.admin_status import AdminRuntimeStatusService
from backend.diagnostics.contracts import (
    ReadinessComponent,
    ReadinessReason,
    ReadinessState,
    RuntimeReadinessReport,
)


class FakeCursor:
    def execute(self, *args: object, **kwargs: object) -> None:
        return None

    def fetchone(self) -> tuple[int]:
        return (0,)

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


class FakeDatabaseClient:
    def connect(self) -> FakeConnection:
        return FakeConnection()


class FailingDatabaseClient:
    def connect(self) -> FakeConnection:
        raise ConnectionError("database credentials must not be exposed")


class FakeReadinessService:
    def check(self) -> RuntimeReadinessReport:
        return RuntimeReadinessReport(
            state=ReadinessState.READY,
            components=(
                ReadinessComponent(
                    name="backend",
                    state=ReadinessState.READY,
                    reason_code=ReadinessReason.CONFIGURED,
                    message="Backend is initialized.",
                ),
            ),
            config={"app_env": "local"},
        )


class FakeMCPAdapter:
    def build_sdk_status(self) -> dict[str, object]:
        return {
            "package_available": True,
            "sdk_version": "1.0",
            "sdk_stable_line": "v1",
            "transport_mode": "registry",
            "server_runtime": "preview",
            "sdk_tool_names": [
                "knowledge.search",
                "risk.score_account",
                "trade.query_metrics",
                "ops.create_alert_or_action",
            ],
            "integration_mode": "sdk_ready",
            "recommended_next_step": "Keep registry transport as the default.",
            "client_symbols": ["Client"],
        }


def build_service() -> AdminRuntimeStatusService:
    settings = SimpleNamespace(
        app_name="Trading and Risk Agentic Platform",
        app_env="local",
        auth_mode="demo",
        retrieval_enabled=True,
        embedding_provider="local_sentence_transformer",
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dimensions=384,
        response_cache_enabled=False,
        mcp_transport_mode="registry",
        mcp_server_runtime="preview",
    )
    return AdminRuntimeStatusService(
        settings=settings,
        database_client=FakeDatabaseClient(),
        readiness_service=FakeReadinessService(),
        mcp_sdk_adapter=FakeMCPAdapter(),
        project_root=Path("/tmp"),
    )


def test_admin_runtime_status_service_aggregates_safe_runtime_views() -> None:
    payload = build_service().build_report().to_payload()

    assert payload["environment"] == "local"
    assert payload["readiness"]["state"] == "ready"
    assert payload["runtime_mode"]["auth_mode"] == "demo"
    assert payload["migration"] == {
        "state": "ready",
        "expected_count": 0,
        "applied_count": 0,
        "reason": "migration_scripts_applied",
    }
    assert payload["mcp"]["sdk_tool_names"] == [
        "knowledge.search",
        "risk.score_account",
        "trade.query_metrics",
        "ops.create_alert_or_action",
    ]
    assert "client_symbols" not in payload["mcp"]


def test_admin_runtime_status_service_redacts_migration_failure_details() -> None:
    service = build_service()
    service.database_client = FailingDatabaseClient()

    migration = service.build_report().to_payload()["migration"]

    assert migration == {
        "state": "unavailable",
        "expected_count": 0,
        "applied_count": None,
        "reason": "migration_status_check_failed",
    }
    assert "credentials" not in str(migration)
