from contextlib import contextmanager

from backend.observability.context import reset_request_id, set_request_id
from backend.services.runtime_switches import RuntimeSwitchService
from backend.storage.db import SQLStatement
from backend.storage.repositories.audit_events import AuditEventRepository
from backend.storage.repositories.runtime_switches import RuntimeSwitchRepository


class FakeExecutor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def execute(self, statement: SQLStatement) -> None:
        _ = statement

    def fetch_all(self, statement: SQLStatement) -> list[dict[str, object]]:
        _ = statement
        return self.rows


class FakeTransaction:
    def __init__(self) -> None:
        self.executed: list[SQLStatement] = []

    def execute(self, statement: SQLStatement) -> None:
        self.executed.append(statement)


class FakeDatabaseClient:
    def __init__(self, transaction: FakeTransaction) -> None:
        self._transaction = transaction

    @contextmanager
    def transaction(self):
        yield self._transaction


def build_service(
    rows: list[dict[str, object]],
    transaction: FakeTransaction | None = None,
) -> RuntimeSwitchService:
    executor = FakeExecutor(rows)
    return RuntimeSwitchService(
        database_client=FakeDatabaseClient(transaction or FakeTransaction()),
        runtime_switch_repository=RuntimeSwitchRepository(executor=executor),
        audit_event_repository=AuditEventRepository(executor=executor),
    )


def test_runtime_switches_merge_persisted_values_with_allowlisted_defaults() -> None:
    service = build_service(
        [{"switch_key": "retrieval_enabled", "is_enabled": False}]
    )

    states = {state.key: state for state in service.list_switches()}

    assert states["retrieval_enabled"].is_enabled is False
    assert states["response_cache_enabled"].is_enabled is True
    assert service.is_enabled("unsupported", False) is False


def test_set_runtime_switch_writes_audit_event_with_request_id() -> None:
    transaction = FakeTransaction()
    service = build_service([], transaction)
    context_token = set_request_id("78bb5a9e-9bc9-4867-aee2-e01922ab6bd9")
    try:
        state = service.set_enabled(
            key="maintenance_mode",
            is_enabled=True,
            actor_user_id=4,
        )
    finally:
        reset_request_id(context_token)

    assert state.is_enabled is True
    assert "INSERT INTO iam.runtime_switches" in transaction.executed[0].sql
    assert transaction.executed[1].params["event_type"] == "admin_runtime_switch_updated"
    assert transaction.executed[1].params["request_id"] == "78bb5a9e-9bc9-4867-aee2-e01922ab6bd9"


def test_runtime_switch_read_failure_falls_back_to_runtime_default() -> None:
    class FailingRepository:
        def list_runtime_switches(self) -> list[dict[str, object]]:
            raise RuntimeError("database unavailable")

    service = RuntimeSwitchService(
        database_client=FakeDatabaseClient(FakeTransaction()),
        runtime_switch_repository=FailingRepository(),  # type: ignore[arg-type]
        audit_event_repository=AuditEventRepository(executor=FakeExecutor([])),
    )

    assert service.is_enabled("retrieval_enabled", True) is True
