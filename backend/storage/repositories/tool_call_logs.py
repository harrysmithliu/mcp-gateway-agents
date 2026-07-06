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
