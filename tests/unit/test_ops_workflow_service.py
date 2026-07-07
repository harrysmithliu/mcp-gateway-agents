from dataclasses import dataclass

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


@dataclass(slots=True)
class FakeStorageBundle:
    risk_alert_repository: FakeRiskAlertRepository


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
    repository = FakeRiskAlertRepository(alerts=[], updates=[])
    service = OpsWorkflowService(
        storage_bundle=FakeStorageBundle(risk_alert_repository=repository)
    )

    response_payload = service.update_alert_status("alert-1", "closed")

    assert response_payload["update_status"] == "completed"
    assert repository.updates == [("alert-1", "closed")]
