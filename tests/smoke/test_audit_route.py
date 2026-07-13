import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_audit_recent_events_route_returns_stable_payload() -> None:
    client = TestClient(app)

    response = client.get(
        "/audit/recent-events?limit=5",
        headers={"x-demo-user": "supervisor_demo"},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["limit"] == 5
    assert payload["query_status"] in {"completed", "degraded"}
    assert isinstance(payload["events"], list)


def test_audit_tool_invocations_route_returns_stable_payload() -> None:
    client = TestClient(app)

    response = client.get(
        "/audit/tool-invocations?limit=5&tool_name=knowledge.search",
        headers={"x-demo-user": "supervisor_demo"},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["limit"] == 5
    assert payload["tool_name"] == "knowledge.search"
    assert payload["query_status"] in {"completed", "degraded"}
    assert isinstance(payload["tool_calls"], list)
