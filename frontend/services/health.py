from dataclasses import dataclass

from frontend.services.api import DEFAULT_API_BASE_URL, build_api_client


@dataclass(frozen=True, slots=True)
class RetrievalRuntimeStatus:
    state: str
    enabled: bool
    vector_backend: str
    provider: str | None = None
    model_name: str | None = None
    vector_dimensions: int | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class HealthStatus:
    status: str
    app_name: str
    environment: str
    retrieval: RetrievalRuntimeStatus


def get_health(
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> HealthStatus:
    payload = build_api_client(
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    ).get("/health")
    retrieval_payload = dict(payload.get("retrieval", {}))
    return HealthStatus(
        status=str(payload["status"]),
        app_name=str(payload["app_name"]),
        environment=str(payload["environment"]),
        retrieval=RetrievalRuntimeStatus(
            state=str(retrieval_payload.get("state", "unavailable")),
            enabled=bool(retrieval_payload.get("enabled", False)),
            vector_backend=str(retrieval_payload.get("vector_backend", "unknown")),
            provider=retrieval_payload.get("provider"),
            model_name=retrieval_payload.get("model_name"),
            vector_dimensions=retrieval_payload.get("vector_dimensions"),
            reason=retrieval_payload.get("reason"),
        ),
    )
