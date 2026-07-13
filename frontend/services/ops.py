from frontend.services.api import DEFAULT_API_BASE_URL, build_api_client


def list_alerts(
    limit: int = 10,
    status: str | None = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).get(
        "/ops/alerts",
        {"limit": limit, "status": status},
    )


def update_alert_status(
    alert_id: str,
    status: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).post(
        f"/ops/alerts/{alert_id}/status",
        {"status": status},
    )


def list_approvals(
    limit: int = 20,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).get(
        "/ops/approvals",
        {"limit": limit},
    )


def request_approval(
    alert_id: str,
    reason: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).post(
        f"/ops/alerts/{alert_id}/approval",
        {"reason": reason},
    )


def decide_approval(
    approval_id: str,
    decision: str,
    reason: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).post(
        f"/ops/approvals/{approval_id}/decision",
        {"decision": decision, "reason": reason},
    )
