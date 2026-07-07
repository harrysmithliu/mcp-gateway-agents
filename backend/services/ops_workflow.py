from dataclasses import dataclass

from backend.storage.runtime import StorageBundle


@dataclass(slots=True)
class OpsWorkflowService:
    storage_bundle: StorageBundle

    def list_recent_alerts(
        self,
        limit: int = 10,
        status: str | None = None,
    ) -> dict[str, object]:
        try:
            alerts = self.storage_bundle.risk_alert_repository.list_recent_alerts(
                limit=limit,
                status=status,
            )
            return {
                "limit": limit,
                "status": status,
                "query_status": "completed",
                "alerts": alerts,
            }
        except Exception:
            return {
                "limit": limit,
                "status": status,
                "query_status": "degraded",
                "alerts": [],
            }

    def update_alert_status(
        self,
        alert_id: str,
        status: str,
    ) -> dict[str, object]:
        try:
            self.storage_bundle.risk_alert_repository.update_alert_status(
                alert_id=alert_id,
                status=status,
            )
            return {
                "alert_id": alert_id,
                "status": status,
                "update_status": "completed",
            }
        except Exception:
            return {
                "alert_id": alert_id,
                "status": status,
                "update_status": "degraded",
            }
