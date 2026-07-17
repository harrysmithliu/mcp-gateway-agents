from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.smoke.http_helpers import assert_success, build_demo_client


def test_admin_runtime_status_returns_redacted_operational_view() -> None:
    payload = assert_success(
        build_demo_client("admin_demo").get("/admin/runtime-status")
    )

    assert payload["environment"]
    assert "observed_at" in payload
    assert payload["readiness"]["state"] in {
        "ready",
        "degraded",
        "unavailable",
    }
    assert payload["migration"]["state"] in {
        "ready",
        "degraded",
        "unavailable",
    }
    assert payload["mcp"]["transport_mode"] == "registry"
    assert "password" not in str(payload)
    assert "token" not in str(payload)
    assert "api_key" not in str(payload)


def test_non_admin_roles_cannot_access_runtime_status() -> None:
    for username in (
        "analyst_demo",
        "risk_operator_demo",
        "supervisor_demo",
    ):
        response = build_demo_client(username).get("/admin/runtime-status")
        assert response.status_code == 403
