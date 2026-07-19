from contextlib import contextmanager

import pytest

from backend.auth.passwords import PasswordService
from backend.observability.context import reset_request_id, set_request_id
from backend.services.admin_identity import (
    AdminIdentityService,
    LastActiveAdminError,
)
from backend.storage.db import SQLStatement
from backend.storage.repositories.audit_events import AuditEventRepository
from backend.storage.repositories.identity import IdentityRepository


class FakeExecutor:
    def execute(self, statement: SQLStatement) -> None:
        _ = statement

    def fetch_all(self, statement: SQLStatement) -> list[dict[str, object]]:
        _ = statement
        return []


class FakeTransaction:
    def __init__(self, responses: list[list[dict[str, object]]]) -> None:
        self.responses = responses
        self.executed: list[SQLStatement] = []

    def execute(self, statement: SQLStatement) -> None:
        self.executed.append(statement)

    def fetch_all(self, statement: SQLStatement) -> list[dict[str, object]]:
        _ = statement
        return self.responses.pop(0)


class FakeDatabaseClient:
    def __init__(self, transaction: FakeTransaction) -> None:
        self._transaction = transaction

    @contextmanager
    def transaction(self):
        yield self._transaction


def build_service(transaction: FakeTransaction) -> AdminIdentityService:
    executor = FakeExecutor()
    return AdminIdentityService(
        database_client=FakeDatabaseClient(transaction),
        identity_repository=IdentityRepository(executor=executor),
        audit_event_repository=AuditEventRepository(executor=executor),
        password_service=PasswordService(),
    )


def test_create_user_writes_credentials_roles_and_audit_event() -> None:
    transaction = FakeTransaction(
        [
            [
                {
                    "user_id": 42,
                    "username": "new_analyst",
                    "display_name": "New Analyst",
                    "is_active": True,
                }
            ]
        ]
    )
    request_token = set_request_id("78bb5a9e-9bc9-4867-aee2-e01922ab6bd9")
    try:
        user = build_service(transaction).create_user(
            username="New_Analyst",
            display_name="New Analyst",
            password="sufficient-local-password",
            roles=["analyst"],
            actor_user_id=4,
        )
    finally:
        reset_request_id(request_token)

    assert user.username == "new_analyst"
    assert user.roles == ("analyst",)
    assert "INSERT INTO iam.user_credentials" in transaction.executed[0].sql
    assert "DELETE FROM iam.user_role_bindings" in transaction.executed[1].sql
    assert "INSERT INTO iam.user_role_bindings" in transaction.executed[2].sql
    assert "INSERT INTO audit.audit_events" in transaction.executed[3].sql
    assert transaction.executed[3].params["request_id"] == "78bb5a9e-9bc9-4867-aee2-e01922ab6bd9"


def test_replace_roles_revokes_existing_sessions() -> None:
    transaction = FakeTransaction(
        [
            [
                {
                    "user_id": 42,
                    "username": "new_analyst",
                    "display_name": "New Analyst",
                    "is_active": True,
                    "roles": ["analyst"],
                }
            ]
        ]
    )

    user = build_service(transaction).replace_roles(
        user_id=42,
        roles=["risk_operator", "supervisor"],
        actor_user_id=4,
    )

    assert user.roles == ("risk_operator", "supervisor")
    assert "DELETE FROM iam.user_role_bindings" in transaction.executed[0].sql
    assert "INSERT INTO iam.user_role_bindings" in transaction.executed[1].sql
    assert "UPDATE iam.auth_sessions SET revoked_at = NOW()" in transaction.executed[2].sql
    assert transaction.executed[3].params["event_type"] == "admin_user_roles_replaced"


def test_cannot_disable_the_last_active_administrator() -> None:
    transaction = FakeTransaction(
        [
            [
                {
                    "user_id": 4,
                    "username": "admin_demo",
                    "display_name": "Admin Demo",
                    "is_active": True,
                    "roles": ["admin"],
                }
            ],
            [{"user_id": 4}],
        ]
    )

    with pytest.raises(LastActiveAdminError):
        build_service(transaction).set_user_active(
            user_id=4,
            is_active=False,
            actor_user_id=4,
        )

    assert transaction.executed == []


def test_identity_repository_builds_managed_user_queries() -> None:
    executor = FakeExecutor()
    repository = IdentityRepository(executor=executor)

    statement = repository.build_list_managed_users_statement()
    delete_statement, insert_statement = repository.build_replace_roles_statements(
        user_id=42,
        role_names=("analyst", "supervisor"),
    )

    assert "array_agg(role.role_name" in statement.sql
    assert "DELETE FROM iam.user_role_bindings" in delete_statement.sql
    assert insert_statement.params["role_names"] == ["analyst", "supervisor"]
