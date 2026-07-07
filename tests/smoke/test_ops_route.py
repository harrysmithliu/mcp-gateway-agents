import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_ops_alerts_route_returns_stable_payload() -> None:
    client = TestClient(app)

    response = client.get(
        "/ops/alerts?limit=5&status=open",
        headers={"x-demo-user": "risk_operator_demo"},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["limit"] == 5
    assert payload["status"] == "open"
    assert payload["query_status"] in {"completed", "degraded"}


def test_ops_alert_status_update_route_returns_stable_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/ops/alerts/demo-alert/status",
        json={"status": "closed"},
        headers={"x-demo-user": "supervisor_demo"},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["alert_id"] == "demo-alert"
    assert payload["status"] == "closed"
    assert payload["update_status"] in {"completed", "degraded"}
