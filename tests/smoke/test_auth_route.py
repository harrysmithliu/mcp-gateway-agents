import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app
from backend.api.dependencies import get_auth_service
from backend.auth.models import AuthSessionRecord, AuthenticatedSession, IdentityUser
from backend.auth.service import LoginResult


class FakeAuthService:
    def authenticate(
        self,
        username: str,
        password: str,
        browser_session_id: str | None = None,
    ) -> LoginResult:
        user = IdentityUser(
            user_id=101,
            username=username,
            display_name="Analyst Demo",
            is_active=True,
        )
        session = AuthenticatedSession(
            session=AuthSessionRecord(
                auth_session_id="auth-session-1",
                user_id=101,
                browser_session_id=browser_session_id or "browser-1",
                token_jti="token-jti-1",
                expires_at=datetime.now(timezone.utc),
            ),
            user=user,
            roles=("analyst",),
        )
        return LoginResult(
            access_token="test-access-token",
            session=session,
            expires_in=1800,
        )


def test_login_route_returns_bearer_identity_contract() -> None:
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    try:
        response = TestClient(app).post(
            "/auth/login",
            json={
                "username": "analyst_demo",
                "password": "demo-password",
                "browser_session_id": "browser-1",
            },
        )
    finally:
        app.dependency_overrides.pop(get_auth_service, None)

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "test-access-token",
        "token_type": "bearer",
        "expires_in": 1800,
        "auth_session_id": "auth-session-1",
        "user": {
            "user_id": 101,
            "username": "analyst_demo",
            "display_name": "Analyst Demo",
            "roles": ["analyst"],
        },
    }
