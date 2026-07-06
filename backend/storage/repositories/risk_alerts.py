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
