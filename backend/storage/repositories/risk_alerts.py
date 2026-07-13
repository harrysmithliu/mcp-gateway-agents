from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import RiskAlertRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class RiskAlertRepository:
    executor: StatementExecutor

    def build_create_statement(self, record: RiskAlertRecord) -> SQLStatement:
        return SQLStatement(
            sql=(
                "INSERT INTO risk.risk_alerts "
                "("
                "alert_id, session_id, message_id, actor_user_id, "
                "alert_type, severity, status, summary, details"
                ") "
                "VALUES ("
                "%(alert_id)s, %(session_id)s, %(message_id)s, %(actor_user_id)s, "
                "%(alert_type)s, %(severity)s, %(status)s, %(summary)s, %(details)s"
                ")"
            ),
            params={
                "alert_id": record.alert_id,
                "session_id": record.session_id,
                "message_id": record.message_id,
                "actor_user_id": record.actor_user_id,
                "alert_type": record.alert_type,
                "severity": record.severity,
                "status": record.status,
                "summary": record.summary,
                "details": record.details,
            },
        )

    def create_risk_alert(self, record: RiskAlertRecord) -> SQLStatement:
        statement = self.build_create_statement(record)
        self.executor.execute(statement)
        return statement

    def get_alert(self, alert_id: str) -> dict[str, object] | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT alert_id, session_id, message_id, actor_user_id, alert_type, "
                    "severity, status, summary, details, created_at, updated_at "
                    "FROM risk.risk_alerts WHERE alert_id = %(alert_id)s"
                ),
                params={"alert_id": alert_id},
            )
        )
        return rows[0] if rows else None

    def build_update_status_statement(
        self,
        alert_id: str,
        previous_status: str,
        next_status: str,
    ) -> SQLStatement:
        return SQLStatement(
            sql=(
                "UPDATE risk.risk_alerts SET status = %(next_status)s, updated_at = NOW() "
                "WHERE alert_id = %(alert_id)s AND status = %(previous_status)s "
                "RETURNING alert_id, status"
            ),
            params={
                "alert_id": alert_id,
                "previous_status": previous_status,
                "next_status": next_status,
            },
        )

    def list_recent_alerts(
        self,
        limit: int = 10,
        status: str | None = None,
    ) -> list[dict[str, object]]:
        if status is None:
            statement = SQLStatement(
                sql=(
                    "SELECT alert_id, session_id, message_id, actor_user_id, "
                    "alert_type, severity, status, summary, details "
                    "FROM risk.risk_alerts "
                    "ORDER BY created_at DESC "
                    "LIMIT %(limit)s"
                ),
                params={"limit": limit},
            )
        else:
            statement = SQLStatement(
                sql=(
                    "SELECT alert_id, session_id, message_id, actor_user_id, "
                    "alert_type, severity, status, summary, details "
                    "FROM risk.risk_alerts "
                    "WHERE status = %(status)s "
                    "ORDER BY created_at DESC "
                    "LIMIT %(limit)s"
                ),
                params={"status": status, "limit": limit},
            )
        return self.executor.fetch_all(statement)

    def update_alert_status(
        self,
        alert_id: str,
        status: str,
    ) -> SQLStatement:
        current_alert = self.get_alert(alert_id)
        previous_status = str(current_alert["status"]) if current_alert else ""
        statement = self.build_update_status_statement(
            alert_id=alert_id,
            previous_status=previous_status,
            next_status=status,
        )
        self.executor.execute(statement)
        return statement
