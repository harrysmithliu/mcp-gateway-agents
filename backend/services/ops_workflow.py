from dataclasses import dataclass
from uuid import uuid4

from backend.storage.models import (
    AuditEventRecord,
    RiskAlertApprovalRecord,
    RiskAlertStatusEventRecord,
)
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

    def list_recent_approvals(self, limit: int = 20) -> dict[str, object]:
        try:
            approvals = self.storage_bundle.risk_alert_approval_repository.list_recent_approvals(
                limit=limit
            )
            return {
                "limit": limit,
                "query_status": "completed",
                "approvals": approvals,
            }
        except Exception:
            return {
                "limit": limit,
                "query_status": "degraded",
                "approvals": [],
            }

    def request_alert_approval(
        self,
        alert_id: str,
        reason: str,
        requested_by_user_id: int | None = None,
    ) -> dict[str, object]:
        try:
            if self.storage_bundle.risk_alert_repository.get_alert(alert_id) is None:
                return {
                    "alert_id": alert_id,
                    "approval_status": "not_found",
                }
            existing = self.storage_bundle.risk_alert_approval_repository.get_pending_for_alert(
                alert_id
            )
            if existing is not None:
                return {
                    "alert_id": alert_id,
                    "approval_id": existing["approval_id"],
                    "approval_status": "already_requested",
                }

            approval_id = str(uuid4())
            audit_event_id = str(uuid4())
            approval = RiskAlertApprovalRecord(
                approval_id=approval_id,
                alert_id=alert_id,
                requested_by_user_id=requested_by_user_id,
                approval_status="requested",
                request_reason=reason,
            )
            audit_event = AuditEventRecord(
                event_id=audit_event_id,
                actor_user_id=requested_by_user_id,
                event_type="risk_alert_approval_requested",
                event_summary="Risk alert approval requested.",
                event_payload={
                    "alert_id": alert_id,
                    "approval_id": approval_id,
                    "reason": reason,
                },
            )
            with self.storage_bundle.database_client.transaction() as transaction:
                transaction.execute(
                    self.storage_bundle.risk_alert_approval_repository.build_create_statement(
                        approval
                    )
                )
                transaction.execute(
                    self.storage_bundle.audit_event_repository.build_create_statement(
                        audit_event
                    )
                )
            return {
                "alert_id": alert_id,
                "approval_id": approval_id,
                "approval_status": "requested",
                "audit_event_id": audit_event_id,
            }
        except Exception:
            return {
                "alert_id": alert_id,
                "approval_status": "failed",
                "reason": "alert_approval_request_failed",
            }

    def decide_alert_approval(
        self,
        approval_id: str,
        decision: str,
        reason: str,
        decided_by_user_id: int | None = None,
    ) -> dict[str, object]:
        if decision not in {"approved", "rejected"}:
            return {
                "approval_id": approval_id,
                "approval_status": "invalid_decision",
            }
        try:
            approval = self.storage_bundle.risk_alert_approval_repository.get_approval(
                approval_id
            )
            if approval is None:
                return {
                    "approval_id": approval_id,
                    "approval_status": "not_found",
                }
            if approval["approval_status"] != "requested":
                return {
                    "approval_id": approval_id,
                    "approval_status": "already_decided",
                }

            audit_event_id = str(uuid4())
            audit_event = AuditEventRecord(
                event_id=audit_event_id,
                actor_user_id=decided_by_user_id,
                event_type="risk_alert_approval_decided",
                event_summary=f"Risk alert approval {decision}.",
                event_payload={
                    "approval_id": approval_id,
                    "alert_id": str(approval["alert_id"]),
                    "decision": decision,
                    "reason": reason,
                },
            )
            with self.storage_bundle.database_client.transaction() as transaction:
                updated_rows = transaction.fetch_all(
                    self.storage_bundle.risk_alert_approval_repository.build_decide_statement(
                        approval_id=approval_id,
                        decision=decision,
                        decided_by_user_id=decided_by_user_id,
                        decision_reason=reason,
                    )
                )
                if not updated_rows:
                    return {
                        "approval_id": approval_id,
                        "approval_status": "conflict",
                    }
                transaction.execute(
                    self.storage_bundle.audit_event_repository.build_create_statement(
                        audit_event
                    )
                )
            return {
                "approval_id": approval_id,
                "alert_id": str(approval["alert_id"]),
                "approval_status": decision,
                "audit_event_id": audit_event_id,
            }
        except Exception:
            return {
                "approval_id": approval_id,
                "approval_status": "failed",
                "reason": "alert_approval_decision_failed",
            }
