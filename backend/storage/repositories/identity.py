from dataclasses import dataclass

from backend.auth.models import AuthSessionRecord, AuthenticatedSession, IdentityUser
from backend.storage.db import SQLStatement
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class IdentityRepository:
    executor: StatementExecutor

    def get_user_by_username(self, username: str) -> IdentityUser | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT user_id, username, display_name, is_active "
                    "FROM iam.users WHERE username = %(username)s"
                ),
                params={"username": username},
            )
        )
        return self._build_user(rows[0]) if rows else None

    def get_user(self, user_id: int) -> IdentityUser | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT user_id, username, display_name, is_active "
                    "FROM iam.users WHERE user_id = %(user_id)s"
                ),
                params={"user_id": user_id},
            )
        )
        return self._build_user(rows[0]) if rows else None

    def list_roles(self, user_id: int) -> tuple[str, ...]:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT role.role_name "
                    "FROM iam.user_role_bindings binding "
                    "JOIN iam.roles role ON role.role_id = binding.role_id "
                    "WHERE binding.user_id = %(user_id)s "
                    "ORDER BY role.role_name"
                ),
                params={"user_id": user_id},
            )
        )
        return tuple(str(row["role_name"]) for row in rows)

    def get_password_hash(self, user_id: int) -> str | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT password_hash FROM iam.user_credentials "
                    "WHERE user_id = %(user_id)s"
                ),
                params={"user_id": user_id},
            )
        )
        return str(rows[0]["password_hash"]) if rows else None

    def create_or_update_password_hash(
        self,
        user_id: int,
        password_hash: str,
    ) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO iam.user_credentials (user_id, password_hash) "
                "VALUES (%(user_id)s, %(password_hash)s) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "password_hash = EXCLUDED.password_hash, "
                "password_updated_at = NOW()"
            ),
            params={"user_id": user_id, "password_hash": password_hash},
        )
        self.executor.execute(statement)
        return statement

    def create_auth_session(self, record: AuthSessionRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO iam.auth_sessions "
                "(auth_session_id, user_id, browser_session_id, token_jti, expires_at) "
                "VALUES (%(auth_session_id)s, %(user_id)s, %(browser_session_id)s, "
                "%(token_jti)s, %(expires_at)s)"
            ),
            params={
                "auth_session_id": record.auth_session_id,
                "user_id": record.user_id,
                "browser_session_id": record.browser_session_id,
                "token_jti": record.token_jti,
                "expires_at": record.expires_at,
            },
        )
        self.executor.execute(statement)
        return statement

    def get_active_auth_session(
        self,
        auth_session_id: str,
        token_jti: str,
    ) -> AuthenticatedSession | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT auth_session.auth_session_id, auth_session.user_id, "
                    "auth_session.browser_session_id, auth_session.token_jti, "
                    "auth_session.expires_at, user_record.username, "
                    "user_record.display_name, user_record.is_active "
                    "FROM iam.auth_sessions auth_session "
                    "JOIN iam.users user_record ON user_record.user_id = auth_session.user_id "
                    "WHERE auth_session.auth_session_id = %(auth_session_id)s "
                    "AND auth_session.token_jti = %(token_jti)s "
                    "AND auth_session.revoked_at IS NULL "
                    "AND auth_session.expires_at > NOW()"
                ),
                params={
                    "auth_session_id": auth_session_id,
                    "token_jti": token_jti,
                },
            )
        )
        if not rows:
            return None
        row = rows[0]
        user = self._build_user(row)
        if not user.is_active:
            return None
        return AuthenticatedSession(
            session=AuthSessionRecord(
                auth_session_id=str(row["auth_session_id"]),
                user_id=int(row["user_id"]),
                browser_session_id=str(row["browser_session_id"]),
                token_jti=str(row["token_jti"]),
                expires_at=row["expires_at"],
            ),
            user=user,
            roles=self.list_roles(user.user_id),
        )

    def revoke_auth_session(self, auth_session_id: str) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "UPDATE iam.auth_sessions SET revoked_at = NOW(), last_seen_at = NOW() "
                "WHERE auth_session_id = %(auth_session_id)s "
                "AND revoked_at IS NULL"
            ),
            params={"auth_session_id": auth_session_id},
        )
        self.executor.execute(statement)
        return statement

    def revoke_active_browser_sessions(self, browser_session_id: str) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "UPDATE iam.auth_sessions SET revoked_at = NOW(), last_seen_at = NOW() "
                "WHERE browser_session_id = %(browser_session_id)s "
                "AND revoked_at IS NULL AND expires_at > NOW()"
            ),
            params={"browser_session_id": browser_session_id},
        )
        self.executor.execute(statement)
        return statement

    @staticmethod
    def _build_user(row: dict[str, object]) -> IdentityUser:
        return IdentityUser(
            user_id=int(row["user_id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            is_active=bool(row["is_active"]),
        )
