from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import AuditEventRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class AuditEventRepository:
    executor: StatementExecutor

    def create_audit_event(self, record: AuditEventRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO audit.audit_events "
                "(event_id, actor_user_id, event_type, event_summary, event_payload) "
                "VALUES ("
                "%(event_id)s, %(actor_user_id)s, %(event_type)s, %(event_summary)s, %(event_payload)s"
                ")"
            ),
            params={
                "event_id": record.event_id,
                "actor_user_id": record.actor_user_id,
                "event_type": record.event_type,
                "event_summary": record.event_summary,
                "event_payload": record.event_payload,
            },
        )
        self.executor.execute(statement)
        return statement
