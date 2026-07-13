from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Protocol
from uuid import uuid4

from backend.auth.models import AuthSessionRecord, AuthenticatedSession, IdentityPrincipal
from backend.auth.passwords import PasswordService
from backend.auth.tokens import JWTTokenService, TokenValidationError


class AuthenticationError(ValueError):
    """Raised when a local identity cannot be authenticated."""


class IdentityStore(Protocol):
    def get_user_by_username(self, username: str): ...
    def get_password_hash(self, user_id: int) -> str | None: ...
    def list_roles(self, user_id: int) -> tuple[str, ...]: ...
    def create_auth_session(self, record: AuthSessionRecord) -> object: ...
    def get_active_auth_session(
        self,
        auth_session_id: str,
        token_jti: str,
    ) -> AuthenticatedSession | None: ...
    def revoke_auth_session(self, auth_session_id: str) -> object: ...
    def revoke_active_browser_sessions(self, browser_session_id: str) -> object: ...


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    session: AuthenticatedSession
    expires_in: int


@dataclass(slots=True)
class AuthService:
    identity_store: IdentityStore
    password_service: PasswordService
    token_service: JWTTokenService
    allow_multiple_identities: bool = False

    def authenticate(
        self,
        username: str,
        password: str,
        browser_session_id: str | None = None,
    ) -> LoginResult:
        user = self.identity_store.get_user_by_username(username.strip())
        password_hash = self.identity_store.get_password_hash(user.user_id) if user else None
        if (
            user is None
            or not user.is_active
            or password_hash is None
            or not self.password_service.verify_password(password, password_hash)
        ):
            raise AuthenticationError("Invalid username or password.")

        roles = self.identity_store.list_roles(user.user_id)
        if not roles:
            raise AuthenticationError("Authenticated user has no assigned role.")

        browser_id = browser_session_id or token_urlsafe(24)
        if not self.allow_multiple_identities:
            self.identity_store.revoke_active_browser_sessions(browser_id)

        now = datetime.now(timezone.utc)
        auth_session_id = str(uuid4())
        token_jti = str(uuid4())
        session = AuthSessionRecord(
            auth_session_id=auth_session_id,
            user_id=user.user_id,
            browser_session_id=browser_id,
            token_jti=token_jti,
            expires_at=now + timedelta(seconds=self.token_service.ttl_seconds),
        )
        self.identity_store.create_auth_session(session)
        authenticated_session = AuthenticatedSession(
            session=session,
            user=user,
            roles=roles,
        )
        return LoginResult(
            access_token=self.token_service.issue_token(
                user_id=user.user_id,
                auth_session_id=auth_session_id,
                token_jti=token_jti,
                now=now,
            ),
            session=authenticated_session,
            expires_in=self.token_service.ttl_seconds,
        )

    def principal_from_token(self, token: str) -> IdentityPrincipal:
        try:
            claims = self.token_service.decode_token(token)
            session = self.identity_store.get_active_auth_session(
                auth_session_id=str(claims["sid"]),
                token_jti=str(claims["jti"]),
            )
        except (KeyError, TokenValidationError) as exc:
            raise AuthenticationError("Invalid bearer token.") from exc
        if session is None or str(session.user.user_id) != str(claims["sub"]):
            raise AuthenticationError("Invalid bearer token.")
        return session.principal

    def logout(self, principal: IdentityPrincipal) -> None:
        self.identity_store.revoke_auth_session(principal.auth_session_id)
