from contextlib import AbstractContextManager
from dataclasses import dataclass
import re
from uuid import uuid4

from backend.auth.passwords import PasswordService
from backend.auth.rbac import Role
from backend.observability.context import get_request_id
from backend.storage.db import DatabaseTransaction
from backend.storage.models import AuditEventRecord
from backend.storage.repositories.audit_events import AuditEventRepository
from backend.storage.repositories.identity import IdentityRepository


class AdminIdentityError(ValueError):
    """Raised when an administrator submits an invalid identity change."""


class ManagedUserNotFoundError(AdminIdentityError):
    """Raised when a requested user does not exist."""


class LastActiveAdminError(AdminIdentityError):
    """Raised when a change would remove the final active administrator."""


_USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_MANAGED_ROLES = frozenset(role.value for role in Role)


@dataclass(frozen=True, slots=True)
class ManagedUser:
    user_id: int
    username: str
    display_name: str
    is_active: bool
    roles: tuple[str, ...]

    @classmethod
    def from_row(cls, row: dict[str, object]) -> "ManagedUser":
        roles = tuple(str(role) for role in row.get("roles", []))
        return cls(
            user_id=int(row["user_id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            is_active=bool(row["is_active"]),
            roles=roles,
        )


@dataclass(slots=True)
class AdminIdentityService:
    """Transactional user and RBAC administration over the existing IAM schema."""

    database_client: object
    identity_repository: IdentityRepository
    audit_event_repository: AuditEventRepository
    password_service: PasswordService

    def list_users(self) -> list[ManagedUser]:
        return [
            ManagedUser.from_row(row)
            for row in self.identity_repository.list_managed_users()
        ]

    def create_user(
        self,
        *,
        username: str,
        display_name: str,
        password: str,
        roles: list[str],
        actor_user_id: int,
    ) -> ManagedUser:
        normalized_username = self._validate_username(username)
        normalized_roles = self._validate_roles(roles)
        normalized_display_name = self._validate_display_name(display_name)
        password_hash = self.password_service.hash_password(password)
        with self._transaction() as transaction:
            rows = transaction.fetch_all(
                self.identity_repository.build_create_user_statement(
                    username=normalized_username,
                    display_name=normalized_display_name,
                )
            )
            if not rows:
                raise AdminIdentityError("User creation did not return a user record.")
            user = ManagedUser.from_row({**rows[0], "roles": normalized_roles})
            transaction.execute(
                self.identity_repository.create_or_update_password_hash_statement(
                    user_id=user.user_id,
                    password_hash=password_hash,
                )
            )
            self._replace_roles(transaction, user.user_id, normalized_roles)
            self._write_audit_event(
                transaction,
                actor_user_id=actor_user_id,
                event_type="admin_user_created",
                summary="Administrator created a user.",
                payload={"user_id": user.user_id, "roles": list(normalized_roles)},
            )
        return user

    def replace_roles(
        self,
        *,
        user_id: int,
        roles: list[str],
        actor_user_id: int,
    ) -> ManagedUser:
        normalized_roles = self._validate_roles(roles)
        with self._transaction() as transaction:
            existing = self._get_managed_user(transaction, user_id)
            self._guard_last_active_admin(
                transaction,
                existing=existing,
                next_is_active=existing.is_active,
                next_roles=normalized_roles,
            )
            self._replace_roles(transaction, user_id, normalized_roles)
            transaction.execute(
                self.identity_repository.build_revoke_user_sessions_statement(user_id)
            )
            self._write_audit_event(
                transaction,
                actor_user_id=actor_user_id,
                event_type="admin_user_roles_replaced",
                summary="Administrator replaced user roles.",
                payload={"user_id": user_id, "roles": list(normalized_roles)},
            )
        return ManagedUser(
            user_id=existing.user_id,
            username=existing.username,
            display_name=existing.display_name,
            is_active=existing.is_active,
            roles=normalized_roles,
        )

    def set_user_active(
        self,
        *,
        user_id: int,
        is_active: bool,
        actor_user_id: int,
    ) -> ManagedUser:
        with self._transaction() as transaction:
            existing = self._get_managed_user(transaction, user_id)
            self._guard_last_active_admin(
                transaction,
                existing=existing,
                next_is_active=is_active,
                next_roles=existing.roles,
            )
            transaction.execute(
                self.identity_repository.build_update_user_active_statement(user_id, is_active)
            )
            if not is_active:
                transaction.execute(
                    self.identity_repository.build_revoke_user_sessions_statement(user_id)
                )
            self._write_audit_event(
                transaction,
                actor_user_id=actor_user_id,
                event_type="admin_user_activity_updated",
                summary="Administrator updated user active status.",
                payload={"user_id": user_id, "is_active": is_active},
            )
        return ManagedUser(
            user_id=existing.user_id,
            username=existing.username,
            display_name=existing.display_name,
            is_active=is_active,
            roles=existing.roles,
        )

    def _get_managed_user(
        self,
        transaction: DatabaseTransaction,
        user_id: int,
    ) -> ManagedUser:
        rows = transaction.fetch_all(
            self.identity_repository.build_get_managed_user_statement(user_id)
        )
        if not rows:
            raise ManagedUserNotFoundError("User does not exist.")
        return ManagedUser.from_row(rows[0])

    def _replace_roles(
        self,
        transaction: DatabaseTransaction,
        user_id: int,
        roles: tuple[str, ...],
    ) -> None:
        delete_statement, insert_statement = (
            self.identity_repository.build_replace_roles_statements(user_id, roles)
        )
        transaction.execute(delete_statement)
        transaction.execute(insert_statement)

    def _guard_last_active_admin(
        self,
        transaction: DatabaseTransaction,
        *,
        existing: ManagedUser,
        next_is_active: bool,
        next_roles: tuple[str, ...],
    ) -> None:
        removing_active_admin = (
            existing.is_active
            and Role.ADMIN.value in existing.roles
            and (not next_is_active or Role.ADMIN.value not in next_roles)
        )
        if not removing_active_admin:
            return
        active_admin_rows = transaction.fetch_all(
            self.identity_repository.build_lock_active_admin_users_statement()
        )
        if len(active_admin_rows) <= 1:
            raise LastActiveAdminError("At least one active administrator is required.")

    def _write_audit_event(
        self,
        transaction: DatabaseTransaction,
        *,
        actor_user_id: int,
        event_type: str,
        summary: str,
        payload: dict[str, object],
    ) -> None:
        transaction.execute(
            self.audit_event_repository.build_create_statement(
                AuditEventRecord(
                    event_id=str(uuid4()),
                    actor_user_id=actor_user_id,
                    request_id=get_request_id(),
                    event_type=event_type,
                    event_summary=summary,
                    event_payload=payload,
                )
            )
        )

    def _transaction(self) -> AbstractContextManager[DatabaseTransaction]:
        return self.database_client.transaction()

    @staticmethod
    def _validate_username(username: str) -> str:
        normalized = username.strip().lower()
        if not _USERNAME_PATTERN.fullmatch(normalized):
            raise AdminIdentityError(
                "Username must use 3-64 lowercase letters, digits, or underscores."
            )
        return normalized

    @staticmethod
    def _validate_display_name(display_name: str) -> str:
        normalized = display_name.strip()
        if not normalized or len(normalized) > 120:
            raise AdminIdentityError("Display name must contain 1-120 characters.")
        return normalized

    @staticmethod
    def _validate_roles(roles: list[str]) -> tuple[str, ...]:
        normalized = tuple(sorted({role.strip().lower() for role in roles if role.strip()}))
        if not normalized or not set(normalized).issubset(_MANAGED_ROLES):
            raise AdminIdentityError("At least one supported role is required.")
        return normalized
