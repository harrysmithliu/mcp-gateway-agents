from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.dependencies import get_runtime_switch_service
from backend.services.runtime_switches import RuntimeSwitchError, RuntimeSwitchState


class FakeRuntimeSwitchService:
    def __init__(self, maintenance_enabled: bool = False) -> None:
        self.maintenance_enabled = maintenance_enabled

    def is_enabled(self, key: str, default: bool) -> bool:
        if key == "maintenance_mode":
            return self.maintenance_enabled
        return default

    def list_switches(self) -> list[RuntimeSwitchState]:
        return [
            RuntimeSwitchState(
                key="maintenance_mode",
                is_enabled=self.maintenance_enabled,
                default_enabled=False,
                description="Temporarily block non-admin application workflows.",
            ),
            RuntimeSwitchState(
                key="retrieval_enabled",
                is_enabled=True,
                default_enabled=True,
                description="Allow RAG retrieval.",
            ),
        ]

    def set_enabled(
        self,
        *,
        key: str,
        is_enabled: bool,
        actor_user_id: int,
    ) -> RuntimeSwitchState:
        _ = actor_user_id
        if key != "maintenance_mode":
            raise RuntimeSwitchError("Unsupported runtime switch.")
        self.maintenance_enabled = is_enabled
        return self.list_switches()[0]


def test_admin_can_list_and_update_allowlisted_runtime_switches() -> None:
    service = FakeRuntimeSwitchService()
    app.dependency_overrides[get_runtime_switch_service] = lambda: service
    try:
        client = TestClient(app)
        client.headers.update({"x-demo-user": "admin_demo"})
        listed = client.get("/admin/runtime-switches")
        updated = client.put(
            "/admin/runtime-switches/maintenance_mode",
            json={"is_enabled": True},
        )
    finally:
        app.dependency_overrides.pop(get_runtime_switch_service, None)

    assert listed.status_code == 200
    assert listed.json()[0]["key"] == "maintenance_mode"
    assert updated.status_code == 200
    assert updated.json()["is_enabled"] is True


def test_non_admin_cannot_access_runtime_switches() -> None:
    response = TestClient(
        app,
        headers={"x-demo-user": "analyst_demo"},
    ).get("/admin/runtime-switches")

    assert response.status_code == 403


def test_maintenance_mode_blocks_non_admin_paths_but_keeps_recovery_paths_available() -> None:
    original_service = app.state.container.runtime_switch_service
    app.state.container.runtime_switch_service = FakeRuntimeSwitchService(
        maintenance_enabled=True
    )
    try:
        client = TestClient(app)
        blocked = client.get("/auth/demo-users")
        health = client.get("/health")
        admin = client.get("/admin/runtime-status", headers={"x-demo-user": "admin_demo"})
    finally:
        app.state.container.runtime_switch_service = original_service

    assert blocked.status_code == 503
    assert health.status_code == 200
    assert admin.status_code == 200
