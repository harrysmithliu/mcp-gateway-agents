import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_auth_demo_users_route_returns_seeded_users() -> None:
    client = TestClient(app)

    response = client.get("/auth/demo-users")

    assert response.status_code == 200

    payload = response.json()
    assert payload["default_user"] == "analyst_demo"
    assert len(payload["users"]) >= 4
