from dataclasses import dataclass

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
