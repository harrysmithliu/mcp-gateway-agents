from frontend.services.api import DEFAULT_API_BASE_URL, build_api_client


def list_knowledge_ingestion_runs(
    limit: int = 20,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).get(
        "/admin/knowledge/ingestion-runs",
        {"limit": limit},
    )


def trigger_knowledge_ingestion(
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 30.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).post(
        "/admin/knowledge/ingestion-runs",
    )


def get_knowledge_ingestion_run(
    run_id: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).get(
        f"/admin/knowledge/ingestion-runs/{run_id}",
    )
