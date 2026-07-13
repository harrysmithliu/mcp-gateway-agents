from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import ToolCallLogRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class ToolCallLogRepository:
    executor: StatementExecutor

    def create_tool_call_log(self, record: ToolCallLogRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO audit.tool_call_logs "
                "("
                "tool_call_id, session_id, message_id, actor_user_id, "
                "tool_namespace, tool_name, call_status, request_payload, "
                "response_payload, error_message, latency_ms"
                ") "
                "VALUES ("
                "%(tool_call_id)s, %(session_id)s, %(message_id)s, %(actor_user_id)s, "
                "%(tool_namespace)s, %(tool_name)s, %(call_status)s, %(request_payload)s, "
                "%(response_payload)s, %(error_message)s, %(latency_ms)s"
                ")"
            ),
            params={
                "tool_call_id": record.tool_call_id,
                "session_id": record.session_id,
                "message_id": record.message_id,
                "actor_user_id": record.actor_user_id,
                "tool_namespace": record.tool_namespace,
                "tool_name": record.tool_name,
                "call_status": record.call_status,
                "request_payload": record.request_payload,
                "response_payload": record.response_payload,
                "error_message": record.error_message,
                "latency_ms": record.latency_ms,
            },
        )
        self.executor.execute(statement)
        return statement

    def list_recent_tool_calls(
        self,
        limit: int = 10,
        session_id: str | None = None,
        tool_name: str | None = None,
        call_status: str | None = None,
    ) -> list[dict[str, object]]:
        where_clauses: list[str] = []
        params: dict[str, object] = {"limit": limit}
        if session_id is not None:
            where_clauses.append("session_id = %(session_id)s")
            params["session_id"] = session_id
        if tool_name is not None:
            where_clauses.append("tool_name = %(tool_name)s")
            params["tool_name"] = tool_name
        if call_status is not None:
            where_clauses.append("call_status = %(call_status)s")
            params["call_status"] = call_status

        where_sql = f"WHERE {' AND '.join(where_clauses)} " if where_clauses else ""
        statement = SQLStatement(
            sql=(
                "SELECT tool_call_id, session_id, message_id, actor_user_id, "
                "tool_namespace, tool_name, call_status, request_payload, "
                "response_payload, error_message, latency_ms, created_at "
                "FROM audit.tool_call_logs "
                f"{where_sql}"
                "ORDER BY created_at DESC "
                "LIMIT %(limit)s"
            ),
            params=params,
        )
        return self.executor.fetch_all(statement)
