from dataclasses import dataclass, field
from contextlib import contextmanager

from backend.storage.db import SQLStatement
from backend.services.ops_workflow import OpsWorkflowService


@dataclass(slots=True)
class FakeRiskAlertRepository:
    alerts: list[dict[str, object]]
    updates: list[tuple[str, str]]

    def list_recent_alerts(
        self,
        limit: int = 10,
        status: str | None = None,
    ) -> list[dict[str, object]]:
        filtered_alerts = self.alerts
        if status is not None:
            filtered_alerts = [
                alert for alert in filtered_alerts if alert["status"] == status
            ]
        return filtered_alerts[:limit]

    def update_alert_status(
        self,
        alert_id: str,
        status: str,
    ) -> None:
        self.updates.append((alert_id, status))

    def get_alert(self, alert_id: str) -> dict[str, object] | None:
        return next(
            (alert for alert in self.alerts if alert["alert_id"] == alert_id),
            None,
        )

    def build_update_status_statement(
        self,
        alert_id: str,
        previous_status: str,
        next_status: str,
    ) -> SQLStatement:
        return SQLStatement(
            sql="UPDATE risk.risk_alerts",
            params={
                "alert_id": alert_id,
                "previous_status": previous_status,
                "next_status": next_status,
            },
        )


class FakeStatusEventRepository:
    def build_create_statement(self, record) -> SQLStatement:
        return SQLStatement(
            sql="INSERT INTO risk.risk_alert_status_events",
            params={"event_id": record.event_id},
        )


class FakeAuditEventRepository:
    def build_create_statement(self, record) -> SQLStatement:
        return SQLStatement(
            sql="INSERT INTO audit.audit_events",
            params={"event_id": record.event_id},
        )


class FakeTransaction:
    def __init__(self) -> None:
        self.statements: list[SQLStatement] = []

    def execute(self, statement: SQLStatement) -> None:
        self.statements.append(statement)

    def fetch_all(self, statement: SQLStatement) -> list[dict[str, object]]:
        self.statements.append(statement)
        return [{"alert_id": statement.params["alert_id"], "status": "acknowledged"}]


class FakeDatabaseClient:
    def __init__(self) -> None:
        self.statements: list[SQLStatement] = []

    @contextmanager
    def transaction(self):
        transaction = FakeTransaction()
        yield transaction
        self.statements.extend(transaction.statements)


@dataclass(slots=True)
class FakeStorageBundle:
    risk_alert_repository: FakeRiskAlertRepository
    risk_alert_status_event_repository: FakeStatusEventRepository = field(
        default_factory=FakeStatusEventRepository
    )
    audit_event_repository: FakeAuditEventRepository = field(
        default_factory=FakeAuditEventRepository
    )
    database_client: FakeDatabaseClient = field(default_factory=FakeDatabaseClient)


def test_ops_workflow_service_lists_recent_alerts() -> None:
    service = OpsWorkflowService(
        storage_bundle=FakeStorageBundle(
            risk_alert_repository=FakeRiskAlertRepository(
                alerts=[{"alert_id": "alert-1", "status": "open"}],
                updates=[],
            )
        )
    )

    response_payload = service.list_recent_alerts(limit=5, status="open")

    assert response_payload["query_status"] == "completed"
    assert response_payload["alerts"][0]["alert_id"] == "alert-1"


def test_ops_workflow_service_updates_alert_status() -> None:
    repository = FakeRiskAlertRepository(
        alerts=[{"alert_id": "alert-1", "status": "open"}],
        updates=[],
    )
    storage_bundle = FakeStorageBundle(risk_alert_repository=repository)
    service = OpsWorkflowService(
        storage_bundle=storage_bundle
    )

    response_payload = service.update_alert_status("alert-1", "acknowledged")

    assert response_payload["update_status"] == "completed"
    assert response_payload["previous_status"] == "open"
    assert response_payload["status"] == "acknowledged"
    assert len(storage_bundle.database_client.statements) == 3


def test_ops_workflow_service_rejects_invalid_alert_transition() -> None:
    service = OpsWorkflowService(
        storage_bundle=FakeStorageBundle(
            risk_alert_repository=FakeRiskAlertRepository(
                alerts=[{"alert_id": "alert-1", "status": "open"}],
                updates=[],
            )
        )
    )

    response_payload = service.update_alert_status("alert-1", "pending")

    assert response_payload["update_status"] == "invalid_transition"


def test_ops_workflow_service_reports_missing_alert() -> None:
    service = OpsWorkflowService(
        storage_bundle=FakeStorageBundle(
            risk_alert_repository=FakeRiskAlertRepository(alerts=[], updates=[])
        )
    )

    response_payload = service.update_alert_status("missing-alert", "closed")

    assert response_payload["update_status"] == "not_found"
