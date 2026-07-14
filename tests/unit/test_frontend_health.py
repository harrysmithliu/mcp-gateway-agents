import json

from frontend.services.health import get_health


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_get_health_parses_retrieval_runtime_status(monkeypatch) -> None:
    def fake_urlopen(*args: object, **kwargs: object) -> FakeResponse:
        return FakeResponse(
            {
                "status": "ok",
                "app_name": "Trading and Risk Agentic Platform",
                "environment": "local",
                "retrieval": {
                    "state": "disabled",
                    "enabled": False,
                    "vector_backend": "postgresql-pgvector",
                    "reason": "disabled_by_configuration",
                },
            }
        )

    monkeypatch.setattr("frontend.services.api.request.urlopen", fake_urlopen)

    health = get_health(api_base_url="http://api.test")

    assert health.app_name == "Trading and Risk Agentic Platform"
    assert health.retrieval.state == "disabled"
    assert health.retrieval.enabled is False
    assert health.retrieval.reason == "disabled_by_configuration"
