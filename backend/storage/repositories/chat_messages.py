from dataclasses import dataclass

from backend.agent.models import ChatHistoryMessage
from backend.storage.db import SQLStatement
from backend.storage.models import ChatMessageRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class ChatMessageRepository:
    executor: StatementExecutor

    def append_message(self, record: ChatMessageRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO convo.chat_messages "
                "(message_id, session_id, sender_type, message_text) "
                "VALUES (%(message_id)s, %(session_id)s, %(sender_type)s, %(message_text)s)"
            ),
            params={
                "message_id": record.message_id,
                "session_id": record.session_id,
                "sender_type": record.sender_type,
                "message_text": record.message_text,
            },
        )
        self.executor.execute(statement)
        return statement

    def list_recent_messages(
        self,
        session_id: str,
        limit: int = 6,
    ) -> list[ChatHistoryMessage]:
        bounded_limit = max(1, min(limit, 50))
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT sender_type, message_text "
                    "FROM ("
                    "SELECT sender_type, message_text, created_at, message_id "
                    "FROM convo.chat_messages "
                    "WHERE session_id = %(session_id)s "
                    "ORDER BY created_at DESC, message_id DESC "
                    "LIMIT %(limit)s"
                    ") recent_messages "
                    "ORDER BY created_at ASC, message_id ASC"
                ),
                params={"session_id": session_id, "limit": bounded_limit},
            )
        )
        return [
            ChatHistoryMessage(
                role=str(row["sender_type"]),
                content=str(row["message_text"]),
            )
            for row in rows
            if row.get("sender_type") is not None
            and row.get("message_text") is not None
        ]
