import json

import pytest

from frontend.services.api import ApiError, build_api_client
from frontend.services.knowledge_ingestion import (
    list_knowledge_ingestion_runs,
    trigger_knowledge_ingestion,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def close(self) -> None:
        return None


def test_api_client_builds_authenticated_get_request(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(api_request, timeout: float) -> FakeResponse:
        captured["url"] = api_request.full_url
        captured["authorization"] = api_request.headers.get("Authorization")
        captured["timeout"] = timeout
        return FakeResponse({"query_status": "completed"})

    monkeypatch.setattr("frontend.services.api.request.urlopen", fake_urlopen)

    response = build_api_client(
        access_token="token-1",
        api_base_url="http://api.test",
        timeout_seconds=8.0,
    ).get("/audit/recent-events", {"limit": 5, "event_type": None})

    assert response["query_status"] == "completed"
    assert captured == {
        "url": "http://api.test/audit/recent-events?limit=5",
        "authorization": "Bearer token-1",
        "timeout": 8.0,
    }


def test_api_client_maps_http_error_to_api_error(monkeypatch) -> None:
    from urllib.error import HTTPError

    def fake_urlopen(*args: object, **kwargs: object) -> None:
        raise HTTPError(
            url="http://api.test/auth/login",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=FakeResponse({"detail": "Bearer authentication is required."}),
        )

    monkeypatch.setattr("frontend.services.api.request.urlopen", fake_urlopen)

    with pytest.raises(ApiError, match="Bearer authentication is required") as exc_info:
        build_api_client(api_base_url="http://api.test").get("/auth/me")

    assert exc_info.value.status_code == 401


def test_knowledge_ingestion_client_uses_admin_endpoints(monkeypatch) -> None:
    captured: list[tuple[str, str, object]] = []

    class FakeClient:
        def get(self, endpoint_path, query=None):
            captured.append(("GET", endpoint_path, query))
            return {"query_status": "completed", "runs": []}

        def post(self, endpoint_path, payload=None):
            captured.append(("POST", endpoint_path, payload))
            return {"run": {"status": "succeeded"}, "sources": []}

    monkeypatch.setattr(
        "frontend.services.knowledge_ingestion.build_api_client",
        lambda *args, **kwargs: FakeClient(),
    )

    assert list_knowledge_ingestion_runs(access_token="token")["runs"] == []
    assert trigger_knowledge_ingestion(access_token="token")["run"]["status"] == "succeeded"
    assert captured == [
        ("GET", "/admin/knowledge/ingestion-runs", {"limit": 20}),
        ("POST", "/admin/knowledge/ingestion-runs", None),
    ]
