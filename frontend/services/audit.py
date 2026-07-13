from frontend.services.api import DEFAULT_API_BASE_URL, build_api_client


def list_audit_events(
    limit: int = 20,
    event_type: str | None = None,
    session_id: str | None = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).get(
        "/audit/recent-events",
        {
            "limit": limit,
            "event_type": event_type,
            "session_id": session_id,
        },
    )


def list_tool_invocations(
    limit: int = 20,
    tool_name: str | None = None,
    call_status: str | None = None,
    session_id: str | None = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).get(
        "/audit/tool-invocations",
        {
            "limit": limit,
            "tool_name": tool_name,
            "call_status": call_status,
            "session_id": session_id,
        },
    )
