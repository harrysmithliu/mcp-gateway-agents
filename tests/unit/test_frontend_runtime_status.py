import json

from frontend.services.runtime_status import get_admin_runtime_status


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_get_admin_runtime_status_parses_safe_runtime_payload(monkeypatch) -> None:
    def fake_urlopen(*args: object, **kwargs: object) -> FakeResponse:
        return FakeResponse(
            {
                "observed_at": "2026-07-17T12:00:00+00:00",
                "environment": "local",
                "readiness": {"state": "degraded", "components": []},
                "runtime_mode": {"auth_mode": "local_jwt"},
                "migration": {"state": "ready", "applied_count": 12},
                "mcp": {"transport_mode": "registry", "tool_count": 1},
            }
        )

    monkeypatch.setattr("frontend.services.api.request.urlopen", fake_urlopen)

    status = get_admin_runtime_status(
        access_token="admin-access-token",
        api_base_url="http://api.test",
    )

    assert status.environment == "local"
    assert status.readiness["state"] == "degraded"
    assert status.runtime_mode["auth_mode"] == "local_jwt"
    assert status.migration["applied_count"] == 12
    assert status.mcp["transport_mode"] == "registry"
