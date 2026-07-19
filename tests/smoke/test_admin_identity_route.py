from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.dependencies import get_admin_identity_service
from backend.services.admin_identity import ManagedUser, ManagedUserNotFoundError


class FakeAdminIdentityService:
    def __init__(self) -> None:
        self.users = [
            ManagedUser(
                user_id=4,
                username="admin_demo",
                display_name="Admin Demo",
                is_active=True,
                roles=("admin",),
            )
        ]

    def list_users(self) -> list[ManagedUser]:
        return self.users

    def create_user(
        self,
        *,
        username: str,
        display_name: str,
        password: str,
        roles: list[str],
        actor_user_id: int,
    ) -> ManagedUser:
        _ = password, actor_user_id
        user = ManagedUser(
            user_id=42,
            username=username.lower(),
            display_name=display_name,
            is_active=True,
            roles=tuple(roles),
        )
        self.users.append(user)
        return user

    def replace_roles(
        self,
        *,
        user_id: int,
        roles: list[str],
        actor_user_id: int,
    ) -> ManagedUser:
        _ = actor_user_id
        for user in self.users:
            if user.user_id == user_id:
                return ManagedUser(
                    user_id=user.user_id,
                    username=user.username,
                    display_name=user.display_name,
                    is_active=user.is_active,
                    roles=tuple(roles),
                )
        raise ManagedUserNotFoundError("User does not exist.")

    def set_user_active(
        self,
        *,
        user_id: int,
        is_active: bool,
        actor_user_id: int,
    ) -> ManagedUser:
        _ = actor_user_id
        for user in self.users:
            if user.user_id == user_id:
                return ManagedUser(
                    user_id=user.user_id,
                    username=user.username,
                    display_name=user.display_name,
                    is_active=is_active,
                    roles=user.roles,
                )
        raise ManagedUserNotFoundError("User does not exist.")


def test_admin_user_routes_expose_only_safe_user_fields() -> None:
    service = FakeAdminIdentityService()
    app.dependency_overrides[get_admin_identity_service] = lambda: service
    try:
        client = TestClient(app)
        client.headers.update({"x-demo-user": "admin_demo"})

        listed = client.get("/admin/users")
        created = client.post(
            "/admin/users",
            json={
                "username": "new_analyst",
                "display_name": "New Analyst",
                "password": "sufficient-local-password",
                "roles": ["analyst"],
            },
        )
        roles_replaced = client.put(
            "/admin/users/42/roles",
            json={"roles": ["risk_operator"]},
        )
        activity_updated = client.patch(
            "/admin/users/42/activity",
            json={"is_active": False},
        )
    finally:
        app.dependency_overrides.pop(get_admin_identity_service, None)

    assert listed.status_code == 200
    assert created.status_code == 201
    assert created.json()["username"] == "new_analyst"
    assert "password" not in created.json()
    assert roles_replaced.json()["roles"] == ["risk_operator"]
    assert activity_updated.json()["is_active"] is False


def test_non_admin_cannot_access_admin_user_routes() -> None:
    response = TestClient(app, headers={"x-demo-user": "analyst_demo"}).get("/admin/users")

    assert response.status_code == 403


def test_admin_user_route_returns_not_found_for_unknown_user() -> None:
    app.dependency_overrides[get_admin_identity_service] = FakeAdminIdentityService
    try:
        response = TestClient(
            app,
            headers={"x-demo-user": "admin_demo"},
        ).patch("/admin/users/999/activity", json={"is_active": False})
    finally:
        app.dependency_overrides.pop(get_admin_identity_service, None)

    assert response.status_code == 404
