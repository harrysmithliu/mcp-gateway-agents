from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import KnowledgeChunkRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class KnowledgeChunkRepository:
    executor: StatementExecutor

    def create_chunk(self, record: KnowledgeChunkRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO knowledge.knowledge_chunks "
                "("
                "chunk_id, document_id, chunk_index, chunk_text, chunk_metadata"
                ") "
                "VALUES ("
                "%(chunk_id)s, %(document_id)s, %(chunk_index)s, %(chunk_text)s, %(chunk_metadata)s"
                ") "
                "ON CONFLICT (chunk_id) DO UPDATE SET "
                "document_id = EXCLUDED.document_id, "
                "chunk_index = EXCLUDED.chunk_index, "
                "chunk_text = EXCLUDED.chunk_text, "
                "chunk_metadata = EXCLUDED.chunk_metadata"
            ),
            params={
                "chunk_id": record.chunk_id,
                "document_id": record.document_id,
                "chunk_index": record.chunk_index,
                "chunk_text": record.chunk_text,
                "chunk_metadata": record.chunk_metadata,
            },
        )
        self.executor.execute(statement)
        return statement
