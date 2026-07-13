import json
from dataclasses import dataclass, field
from urllib import error, request


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
    api_base_url: str = "http://localhost:8000",
    timeout_seconds: float = 5.0,
) -> AuthApiResponse:
    payload = json.dumps(
        {
            "username": username,
            "password": password,
        }
    ).encode("utf-8")
    login_request = request.Request(
        url=f"{api_base_url.rstrip('/')}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(login_request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise RuntimeError("Login failed. Check the username and password.") from exc
    except error.URLError as exc:
        raise RuntimeError("Unable to reach the authentication API.") from exc

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
