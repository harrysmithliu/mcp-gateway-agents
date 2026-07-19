from frontend.services.admin_management import (
    create_admin_user,
    list_admin_users,
    set_runtime_switch,
)


class FakeApiClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object] | None]] = []

    def request_json(self, method: str, path: str):
        self.calls.append((method, path, None))
        return [{"user_id": 4, "username": "admin_demo"}]

    def post(self, path: str, payload: dict[str, object]):
        self.calls.append(("POST", path, payload))
        return {"user_id": 42, "username": payload["username"]}

    def put(self, path: str, payload: dict[str, object]):
        self.calls.append(("PUT", path, payload))
        return {"key": "maintenance_mode", **payload}


def test_admin_management_service_targets_safe_admin_endpoints(monkeypatch) -> None:
    client = FakeApiClient()
    monkeypatch.setattr(
        "frontend.services.admin_management.build_api_client",
        lambda *args, **kwargs: client,
    )

    users = list_admin_users(access_token="access-token")
    created = create_admin_user(
        username="new_analyst",
        display_name="New Analyst",
        password="sufficient-local-password",
        roles=["analyst"],
        access_token="access-token",
    )
    updated = set_runtime_switch(
        key="maintenance_mode",
        is_enabled=True,
        access_token="access-token",
    )

    assert users[0]["username"] == "admin_demo"
    assert created["username"] == "new_analyst"
    assert updated["is_enabled"] is True
    assert client.calls == [
        ("GET", "/admin/users", None),
        (
            "POST",
            "/admin/users",
            {
                "username": "new_analyst",
                "display_name": "New Analyst",
                "password": "sufficient-local-password",
                "roles": ["analyst"],
            },
        ),
        ("PUT", "/admin/runtime-switches/maintenance_mode", {"is_enabled": True}),
    ]
