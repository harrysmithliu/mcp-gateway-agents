from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import AuditEventRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class AuditEventRepository:
    executor: StatementExecutor

    def build_create_statement(self, record: AuditEventRecord) -> SQLStatement:
        return SQLStatement(
            sql=(
                "INSERT INTO audit.audit_events "
                "(event_id, actor_user_id, request_id, event_type, event_summary, event_payload) "
                "VALUES ("
                "%(event_id)s, %(actor_user_id)s, %(request_id)s, %(event_type)s, %(event_summary)s, %(event_payload)s"
                ")"
            ),
            params={
                "event_id": record.event_id,
                "actor_user_id": record.actor_user_id,
                "request_id": record.request_id,
                "event_type": record.event_type,
                "event_summary": record.event_summary,
                "event_payload": record.event_payload,
            },
        )

    def create_audit_event(self, record: AuditEventRecord) -> SQLStatement:
        statement = self.build_create_statement(record)
        self.executor.execute(statement)
        return statement

    def list_recent_events(
        self,
        limit: int = 10,
        event_type: str | None = None,
        session_id: str | None = None,
        actor_user_id: int | None = None,
        request_id: str | None = None,
    ) -> list[dict[str, object]]:
        where_clauses: list[str] = []
        params: dict[str, object] = {"limit": limit}
        if event_type is not None:
            where_clauses.append("event_type = %(event_type)s")
            params["event_type"] = event_type
        if session_id is not None:
            where_clauses.append("event_payload ->> 'session_id' = %(session_id)s")
            params["session_id"] = session_id
        if actor_user_id is not None:
            where_clauses.append("actor_user_id = %(actor_user_id)s")
            params["actor_user_id"] = actor_user_id
        if request_id is not None:
            where_clauses.append("request_id = %(request_id)s")
            params["request_id"] = request_id

        where_sql = f"WHERE {' AND '.join(where_clauses)} " if where_clauses else ""
        statement = SQLStatement(
            sql=(
                "SELECT event_id, actor_user_id, request_id, event_type, event_summary, "
                "event_payload, created_at "
                "FROM audit.audit_events "
                f"{where_sql}"
                "ORDER BY created_at DESC "
                "LIMIT %(limit)s"
            ),
            params=params,
        )
        return self.executor.fetch_all(statement)
