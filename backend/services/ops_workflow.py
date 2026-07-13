from dataclasses import dataclass
from uuid import uuid4

from backend.storage.models import AuditEventRecord, RiskAlertStatusEventRecord
from backend.storage.runtime import StorageBundle


@dataclass(slots=True)
class OpsWorkflowService:
    storage_bundle: StorageBundle

    allowed_status_transitions: frozenset[tuple[str, str]] = frozenset(
        {
            ("open", "acknowledged"),
            ("open", "closed"),
            ("acknowledged", "closed"),
        }
    )

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
        actor_user_id: int | None = None,
    ) -> dict[str, object]:
        try:
            current_alert = self.storage_bundle.risk_alert_repository.get_alert(alert_id)
            if current_alert is None:
                return {
                    "alert_id": alert_id,
                    "status": status,
                    "update_status": "not_found",
                }

            previous_status = str(current_alert["status"])
            if (previous_status, status) not in self.allowed_status_transitions:
                return {
                    "alert_id": alert_id,
                    "previous_status": previous_status,
                    "status": status,
                    "update_status": "invalid_transition",
                }

            status_event_id = str(uuid4())
            audit_event_id = str(uuid4())
            status_event = RiskAlertStatusEventRecord(
                event_id=status_event_id,
                alert_id=alert_id,
                actor_user_id=actor_user_id,
                previous_status=previous_status,
                next_status=status,
            )
            audit_event = AuditEventRecord(
                event_id=audit_event_id,
                actor_user_id=actor_user_id,
                event_type="risk_alert_status_changed",
                event_summary=f"Risk alert status changed from {previous_status} to {status}.",
                event_payload={
                    "alert_id": alert_id,
                    "previous_status": previous_status,
                    "next_status": status,
                    "status_event_id": status_event_id,
                },
            )
            with self.storage_bundle.database_client.transaction() as transaction:
                updated_rows = transaction.fetch_all(
                    self.storage_bundle.risk_alert_repository.build_update_status_statement(
                        alert_id=alert_id,
                        previous_status=previous_status,
                        next_status=status,
                    )
                )
                if not updated_rows:
                    return {
                        "alert_id": alert_id,
                        "previous_status": previous_status,
                        "status": status,
                        "update_status": "conflict",
                    }
                transaction.execute(
                    self.storage_bundle.risk_alert_status_event_repository.build_create_statement(
                        status_event
                    )
                )
                transaction.execute(
                    self.storage_bundle.audit_event_repository.build_create_statement(
                        audit_event
                    )
                )
            return {
                "alert_id": alert_id,
                "previous_status": previous_status,
                "status": status,
                "status_event_id": status_event_id,
                "audit_event_id": audit_event_id,
                "update_status": "completed",
            }
        except Exception:
            return {
                "alert_id": alert_id,
                "status": status,
                "update_status": "failed",
                "reason": "alert_status_write_failed",
            }
