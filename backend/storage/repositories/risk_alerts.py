from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import RiskAlertRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class RiskAlertRepository:
    executor: StatementExecutor

    def create_risk_alert(self, record: RiskAlertRecord) -> SQLStatement:
        statement = SQLStatement(
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
        self.executor.execute(statement)
        return statement

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
        statement = SQLStatement(
            sql=(
                "UPDATE risk.risk_alerts "
                "SET status = %(status)s "
                "WHERE alert_id = %(alert_id)s"
            ),
            params={
                "alert_id": alert_id,
                "status": status,
            },
        )
        self.executor.execute(statement)
        return statement
