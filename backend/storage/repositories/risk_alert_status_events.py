from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import RiskAlertStatusEventRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class RiskAlertStatusEventRepository:
    executor: StatementExecutor

    def build_create_statement(
        self,
        record: RiskAlertStatusEventRecord,
    ) -> SQLStatement:
        return SQLStatement(
            sql=(
                "INSERT INTO risk.risk_alert_status_events "
                "(event_id, alert_id, actor_user_id, previous_status, next_status, reason, details) "
                "VALUES ("
                "%(event_id)s, %(alert_id)s, %(actor_user_id)s, %(previous_status)s, "
                "%(next_status)s, %(reason)s, %(details)s"
                ")"
            ),
            params={
                "event_id": record.event_id,
                "alert_id": record.alert_id,
                "actor_user_id": record.actor_user_id,
                "previous_status": record.previous_status,
                "next_status": record.next_status,
                "reason": record.reason,
                "details": record.details,
            },
        )

    def create_event(self, record: RiskAlertStatusEventRecord) -> SQLStatement:
        statement = self.build_create_statement(record)
        self.executor.execute(statement)
        return statement

    def list_for_alert(self, alert_id: str) -> list[dict[str, object]]:
        return self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT event_id, alert_id, actor_user_id, previous_status, "
                    "next_status, reason, details, created_at "
                    "FROM risk.risk_alert_status_events "
                    "WHERE alert_id = %(alert_id)s ORDER BY created_at DESC"
                ),
                params={"alert_id": alert_id},
            )
        )
