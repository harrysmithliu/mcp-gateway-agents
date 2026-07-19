from frontend.services.api import DEFAULT_API_BASE_URL, build_api_client


def list_admin_users(
    *,
    access_token: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> list[dict[str, object]]:
    payload = build_api_client(access_token, api_base_url, timeout_seconds).request_json(
        "GET",
        "/admin/users",
    )
    return list(payload) if isinstance(payload, list) else []


def create_admin_user(
    *,
    username: str,
    display_name: str,
    password: str,
    roles: list[str],
    access_token: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).post(
        "/admin/users",
        {
            "username": username,
            "display_name": display_name,
            "password": password,
            "roles": roles,
        },
    )


def replace_admin_user_roles(
    *,
    user_id: int,
    roles: list[str],
    access_token: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).put(
        f"/admin/users/{user_id}/roles",
        {"roles": roles},
    )


def set_admin_user_activity(
    *,
    user_id: int,
    is_active: bool,
    access_token: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).patch(
        f"/admin/users/{user_id}/activity",
        {"is_active": is_active},
    )


def list_runtime_switches(
    *,
    access_token: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> list[dict[str, object]]:
    payload = build_api_client(access_token, api_base_url, timeout_seconds).request_json(
        "GET",
        "/admin/runtime-switches",
    )
    return list(payload) if isinstance(payload, list) else []


def set_runtime_switch(
    *,
    key: str,
    is_enabled: bool,
    access_token: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).put(
        f"/admin/runtime-switches/{key}",
        {"is_enabled": is_enabled},
    )
