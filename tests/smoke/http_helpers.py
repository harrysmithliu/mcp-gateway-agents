from fastapi.testclient import TestClient

from backend.api.app import app


def build_demo_client(username: str) -> TestClient:
    client = TestClient(app)
    client.headers.update({"x-demo-user": username})
    return client


def assert_success(response) -> dict[str, object]:
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, dict)
    return payload
