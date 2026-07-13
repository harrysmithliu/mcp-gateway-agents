from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class IdentityUser:
    user_id: int
    username: str
    display_name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class IdentityPrincipal:
    user: IdentityUser
    roles: tuple[str, ...]
    auth_session_id: str
    browser_session_id: str

    @property
    def user_id(self) -> int:
        return self.user.user_id

    @property
    def primary_role(self) -> str:
        return self.roles[0] if self.roles else ""


@dataclass(frozen=True, slots=True)
class AuthSessionRecord:
    auth_session_id: str
    user_id: int
    browser_session_id: str
    token_jti: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    session: AuthSessionRecord
    user: IdentityUser
    roles: tuple[str, ...]

    @property
    def principal(self) -> IdentityPrincipal:
        return IdentityPrincipal(
            user=self.user,
            roles=self.roles,
            auth_session_id=self.session.auth_session_id,
            browser_session_id=self.session.browser_session_id,
        )


@dataclass(frozen=True, slots=True)
class UserCredentialRecord:
    user_id: int
    password_hash: str
