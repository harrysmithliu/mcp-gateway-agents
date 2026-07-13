from dataclasses import dataclass, field

from frontend.services.api import ApiError, DEFAULT_API_BASE_URL, build_api_client


@dataclass(slots=True)
class AuthApiResponse:
    access_token: str
    expires_in: int
    auth_session_id: str
    user_id: int
    username: str
    display_name: str
    roles: list[str] = field(default_factory=list)


def post_login(
    username: str,
    password: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> AuthApiResponse:
    try:
        response_payload = build_api_client(
            api_base_url=api_base_url,
            timeout_seconds=timeout_seconds,
        ).post("/auth/login", {"username": username, "password": password})
    except ApiError as exc:
        if exc.status_code == 401:
            raise RuntimeError("Login failed. Check the username and password.") from exc
        raise RuntimeError(str(exc)) from exc

    user = response_payload["user"]
    return AuthApiResponse(
        access_token=str(response_payload["access_token"]),
        expires_in=int(response_payload["expires_in"]),
        auth_session_id=str(response_payload["auth_session_id"]),
        user_id=int(user["user_id"]),
        username=str(user["username"]),
        display_name=str(user["display_name"]),
        roles=list(user.get("roles", [])),
    )
