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

    def list_recent_events(
        self,
        limit: int = 10,
        event_type: str | None = None,
    ) -> list[dict[str, object]]:
        if event_type is None:
            statement = SQLStatement(
                sql=(
                    "SELECT event_id, actor_user_id, event_type, event_summary, "
                    "event_payload, created_at "
                    "FROM audit.audit_events "
                    "ORDER BY created_at DESC "
                    "LIMIT %(limit)s"
                ),
                params={"limit": limit},
            )
        else:
            statement = SQLStatement(
                sql=(
                    "SELECT event_id, actor_user_id, event_type, event_summary, "
                    "event_payload, created_at "
                    "FROM audit.audit_events "
                    "WHERE event_type = %(event_type)s "
                    "ORDER BY created_at DESC "
                    "LIMIT %(limit)s"
                ),
                params={"event_type": event_type, "limit": limit},
            )
        return self.executor.fetch_all(statement)
