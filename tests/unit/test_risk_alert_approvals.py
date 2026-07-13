from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

from backend.services.ops_workflow import OpsWorkflowService
from backend.storage.db import SQLStatement
from backend.storage.models import RiskAlertApprovalRecord
from backend.storage.repositories.risk_alert_approvals import RiskAlertApprovalRepository


class FakeExecutor:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or []
        self.statements: list[SQLStatement] = []

    def execute(self, statement: SQLStatement) -> None:
        self.statements.append(statement)

    def fetch_all(self, statement: SQLStatement) -> list[dict[str, object]]:
        self.statements.append(statement)
        return self.rows


def test_approval_repository_builds_create_and_decide_statements() -> None:
    executor = FakeExecutor()
    repository = RiskAlertApprovalRepository(executor=executor)

    create_statement = repository.create_approval(
        RiskAlertApprovalRecord(
            approval_id="approval-1",
            alert_id="alert-1",
            requested_by_user_id=2,
            approval_status="requested",
            request_reason="Sensitive action needs review.",
        )
    )
    decide_statement = repository.build_decide_statement(
        approval_id="approval-1",
        decision="approved",
        decided_by_user_id=3,
        decision_reason="Evidence reviewed.",
    )

    assert "INSERT INTO risk.risk_alert_approvals" in create_statement.sql
    assert "approval_status = 'requested'" in decide_statement.sql
    assert executor.statements == [create_statement]


class FakeAlertRepository:
    def get_alert(self, alert_id: str) -> dict[str, object] | None:
        return {"alert_id": alert_id, "status": "open"}


class FakeApprovalRepository:
    def __init__(self) -> None:
        self.pending: dict[str, object] | None = None
        self.approval = {
            "approval_id": "approval-1",
            "alert_id": "alert-1",
            "approval_status": "requested",
        }

    def get_pending_for_alert(self, alert_id: str) -> dict[str, object] | None:
        return self.pending

    def get_approval(self, approval_id: str) -> dict[str, object] | None:
        return self.approval if approval_id == "approval-1" else None

    def build_create_statement(self, record: RiskAlertApprovalRecord) -> SQLStatement:
        self.pending = {
            "approval_id": record.approval_id,
            "alert_id": record.alert_id,
            "approval_status": record.approval_status,
        }
        return SQLStatement(sql="INSERT risk approval", params={"approval_id": record.approval_id})

    def build_decide_statement(
        self,
        approval_id: str,
        decision: str,
        decided_by_user_id: int | None,
        decision_reason: str,
    ) -> SQLStatement:
        return SQLStatement(sql="UPDATE risk approval", params={"approval_id": approval_id})

    def list_recent_approvals(self, limit: int) -> list[dict[str, object]]:
        return []


def test_approval_decision_converts_database_uuid_to_audit_safe_text() -> None:
    service = build_service()

    service.storage_bundle.risk_alert_approval_repository.approval["alert_id"] = (
        UUID("3781ce02-e096-4e79-98b0-32a22da8a73a")
    )
    response = service.decide_alert_approval(
        approval_id="approval-1",
        decision="approved",
        reason="Evidence reviewed.",
        decided_by_user_id=3,
    )

    assert response["alert_id"] == "3781ce02-e096-4e79-98b0-32a22da8a73a"


class FakeAuditRepository:
    def build_create_statement(self, record) -> SQLStatement:
        return SQLStatement(sql="INSERT audit event", params={"event_id": record.event_id})


class FakeTransaction:
    def execute(self, statement: SQLStatement) -> None:
        return None

    def fetch_all(self, statement: SQLStatement) -> list[dict[str, object]]:
        return [{"approval_id": statement.params["approval_id"]}]


class FakeDatabaseClient:
    @contextmanager
    def transaction(self):
        yield FakeTransaction()


@dataclass(slots=True)
class FakeStorageBundle:
    risk_alert_repository: FakeAlertRepository
    risk_alert_approval_repository: FakeApprovalRepository
    audit_event_repository: FakeAuditRepository
    database_client: FakeDatabaseClient


def build_service() -> OpsWorkflowService:
    return OpsWorkflowService(
        storage_bundle=FakeStorageBundle(
            risk_alert_repository=FakeAlertRepository(),
            risk_alert_approval_repository=FakeApprovalRepository(),
            audit_event_repository=FakeAuditRepository(),
            database_client=FakeDatabaseClient(),
        )
    )


def test_ops_workflow_requests_and_decides_alert_approval() -> None:
    service = build_service()

    requested = service.request_alert_approval(
        alert_id="alert-1",
        reason="Escalate for supervisor review.",
        requested_by_user_id=2,
    )
    decided = service.decide_alert_approval(
        approval_id="approval-1",
        decision="approved",
        reason="Evidence reviewed.",
        decided_by_user_id=3,
    )

    assert requested["approval_status"] == "requested"
    assert "approval_id" in requested
    assert decided["approval_status"] == "approved"


def test_ops_workflow_rejects_unknown_approval_decision() -> None:
    response = build_service().decide_alert_approval(
        approval_id="approval-1",
        decision="pending",
        reason="Not a final decision.",
    )

    assert response["approval_status"] == "invalid_decision"
