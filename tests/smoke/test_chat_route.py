import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_chat_route_returns_structured_response() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": "Please review trade risk and create an alert.",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert set(payload) == {"reply_text", "tool_names", "evidence", "actions"}
    assert isinstance(payload["reply_text"], str)
    assert isinstance(payload["tool_names"], list)
    assert isinstance(payload["evidence"], list)
    assert isinstance(payload["actions"], list)
