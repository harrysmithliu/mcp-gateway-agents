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
                "VALUES (%(session_id)s, %(user_id)s, %(session_title)s)"
            ),
            params={
                "session_id": record.session_id,
                "user_id": record.user_id,
                "session_title": record.session_title,
            },
        )
        self.executor.execute(statement)
        return statement
