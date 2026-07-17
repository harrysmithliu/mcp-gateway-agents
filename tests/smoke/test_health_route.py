import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_health_route_returns_public_health_payload() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert isinstance(payload["app_name"], str)
    assert isinstance(payload["environment"], str)
    assert payload["retrieval"]["state"] in {"ready", "disabled", "unavailable"}
    assert isinstance(payload["retrieval"]["enabled"], bool)
    assert payload["readiness"]["state"] in {
        "ready",
        "degraded",
        "unavailable",
    }
    assert isinstance(payload["readiness"]["components"], list)
    assert "password" not in str(payload["readiness"])
    assert "token" not in str(payload["readiness"])
