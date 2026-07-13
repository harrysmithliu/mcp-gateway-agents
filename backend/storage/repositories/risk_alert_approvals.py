from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import RiskAlertApprovalRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class RiskAlertApprovalRepository:
    executor: StatementExecutor

    def build_create_statement(self, record: RiskAlertApprovalRecord) -> SQLStatement:
        return SQLStatement(
            sql=(
                "INSERT INTO risk.risk_alert_approvals "
                "(approval_id, alert_id, requested_by_user_id, approval_status, request_reason) "
                "VALUES ("
                "%(approval_id)s, %(alert_id)s, %(requested_by_user_id)s, "
                "%(approval_status)s, %(request_reason)s"
                ")"
            ),
            params={
                "approval_id": record.approval_id,
                "alert_id": record.alert_id,
                "requested_by_user_id": record.requested_by_user_id,
                "approval_status": record.approval_status,
                "request_reason": record.request_reason,
            },
        )

    def create_approval(self, record: RiskAlertApprovalRecord) -> SQLStatement:
        statement = self.build_create_statement(record)
        self.executor.execute(statement)
        return statement

    def get_approval(self, approval_id: str) -> dict[str, object] | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT approval_id, alert_id, requested_by_user_id, decided_by_user_id, "
                    "approval_status, request_reason, decision_reason, requested_at, decided_at "
                    "FROM risk.risk_alert_approvals WHERE approval_id = %(approval_id)s"
                ),
                params={"approval_id": approval_id},
            )
        )
        return rows[0] if rows else None

    def get_pending_for_alert(self, alert_id: str) -> dict[str, object] | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT approval_id, alert_id, requested_by_user_id, decided_by_user_id, "
                    "approval_status, request_reason, decision_reason, requested_at, decided_at "
                    "FROM risk.risk_alert_approvals "
                    "WHERE alert_id = %(alert_id)s AND approval_status = 'requested' "
                    "ORDER BY requested_at DESC LIMIT 1"
                ),
                params={"alert_id": alert_id},
            )
        )
        return rows[0] if rows else None

    def build_decide_statement(
        self,
        approval_id: str,
        decision: str,
        decided_by_user_id: int | None,
        decision_reason: str,
    ) -> SQLStatement:
        return SQLStatement(
            sql=(
                "UPDATE risk.risk_alert_approvals SET "
                "approval_status = %(approval_status)s, "
                "decided_by_user_id = %(decided_by_user_id)s, "
                "decision_reason = %(decision_reason)s, decided_at = NOW() "
                "WHERE approval_id = %(approval_id)s AND approval_status = 'requested' "
                "RETURNING approval_id, approval_status"
            ),
            params={
                "approval_id": approval_id,
                "approval_status": decision,
                "decided_by_user_id": decided_by_user_id,
                "decision_reason": decision_reason,
            },
        )

    def list_recent_approvals(self, limit: int = 20) -> list[dict[str, object]]:
        return self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT approval_id, alert_id, requested_by_user_id, decided_by_user_id, "
                    "approval_status, request_reason, decision_reason, requested_at, decided_at "
                    "FROM risk.risk_alert_approvals ORDER BY requested_at DESC LIMIT %(limit)s"
                ),
                params={"limit": limit},
            )
        )
