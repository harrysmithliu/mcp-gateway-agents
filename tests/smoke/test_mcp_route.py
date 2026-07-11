import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_mcp_sdk_status_route_returns_stable_payload() -> None:
    client = TestClient(app)

    response = client.get("/mcp/sdk-status")

    assert response.status_code == 200

    payload = response.json()
    assert "package_available" in payload
    assert "integration_mode" in payload
    assert "recommended_next_step" in payload
    assert payload["transport_mode"] == "registry"
    assert payload["server_runtime"] == "preview"
    assert payload["sdk_tool_names"] == ["knowledge.search"]
