from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import ChatSessionRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class ChatSessionRepository:
    executor: StatementExecutor

    def create_session(self, record: ChatSessionRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO convo.chat_sessions "
                "(session_id, user_id, session_title) "
                "VALUES (%(session_id)s, %(user_id)s, %(session_title)s) "
                "ON CONFLICT (session_id) DO NOTHING"
            ),
            params={
                "session_id": record.session_id,
                "user_id": record.user_id,
                "session_title": record.session_title,
            },
        )
        self.executor.execute(statement)
        return statement

    def get_session(self, session_id: str) -> dict[str, object] | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT session_id, user_id, session_title "
                    "FROM convo.chat_sessions WHERE session_id = %(session_id)s"
                ),
                params={"session_id": session_id},
            )
        )
        return rows[0] if rows else None

    def claim_session(self, session_id: str, user_id: int) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "UPDATE convo.chat_sessions SET user_id = %(user_id)s, updated_at = NOW() "
                "WHERE session_id = %(session_id)s AND user_id IS NULL"
            ),
            params={"session_id": session_id, "user_id": user_id},
        )
        self.executor.execute(statement)
        return statement
