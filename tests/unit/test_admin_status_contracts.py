from datetime import datetime, timezone

from backend.diagnostics.contracts import (
    AdminRuntimeStatusReport,
    ReadinessComponent,
    ReadinessReason,
    ReadinessState,
    RuntimeReadinessReport,
)


def _build_report(**kwargs: object) -> AdminRuntimeStatusReport:
    return AdminRuntimeStatusReport(
        observed_at=datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc),
        environment="local",
        readiness=RuntimeReadinessReport(
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
        ),
        **kwargs,
    )


def test_admin_runtime_status_serializes_stable_projection() -> None:
    payload = _build_report(
        runtime_mode={"auth_mode": "local_jwt", "mcp_transport_mode": "registry"},
        migration={"state": "ready", "applied_count": 12},
        mcp={"package_available": True, "tool_count": 1},
    ).to_payload()

    assert payload == {
        "observed_at": "2026-07-17T12:00:00+00:00",
        "environment": "local",
        "readiness": {
            "state": "ready",
            "components": [
                {
                    "name": "backend",
                    "state": "ready",
                    "reason_code": "configured",
                    "message": "Backend is initialized.",
                    "remediation": None,
                    "details": {},
                }
            ],
            "config": {"app_env": "local"},
        },
        "runtime_mode": {"auth_mode": "local_jwt", "mcp_transport_mode": "registry"},
        "migration": {"state": "ready", "applied_count": 12},
        "mcp": {"package_available": True, "tool_count": 1},
    }


def test_admin_runtime_status_does_not_serialize_sensitive_fields() -> None:
    payload = _build_report(
        runtime_mode={
            "auth_mode": "local_jwt",
            "database_url": "postgresql://user:password@localhost/db",
            "anthropic_api_key": "do-not-return",
        },
        migration={"state": "ready", "connection_credential": "hidden"},
        mcp={"token": "hidden", "tool_count": 1},
    ).to_payload()

    assert payload["runtime_mode"] == {"auth_mode": "local_jwt"}
    assert payload["migration"] == {"state": "ready"}
    assert payload["mcp"] == {"tool_count": 1}
    assert "password" not in str(payload)
    assert "do-not-return" not in str(payload)
