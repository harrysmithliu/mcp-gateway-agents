from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import KnowledgeDocumentRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class KnowledgeDocumentRepository:
    executor: StatementExecutor

    def create_document(self, record: KnowledgeDocumentRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO knowledge.knowledge_documents "
                "("
                "document_id, title, content_type, access_level, "
                "jurisdiction, file_path, tags, content_checksum_sha256, "
                "index_fingerprint"
                ") "
                "VALUES ("
                "%(document_id)s, %(title)s, %(content_type)s, %(access_level)s, "
                "%(jurisdiction)s, %(file_path)s, %(tags)s, "
                "%(content_checksum_sha256)s, %(index_fingerprint)s"
                ") "
                "ON CONFLICT (document_id) DO UPDATE SET "
                "title = EXCLUDED.title, "
                "content_type = EXCLUDED.content_type, "
                "access_level = EXCLUDED.access_level, "
                "jurisdiction = EXCLUDED.jurisdiction, "
                "file_path = EXCLUDED.file_path, "
                "tags = EXCLUDED.tags, "
                "content_checksum_sha256 = EXCLUDED.content_checksum_sha256, "
                "index_fingerprint = EXCLUDED.index_fingerprint, "
                "updated_at = NOW()"
            ),
            params={
                "document_id": record.document_id,
                "title": record.title,
                "content_type": record.content_type,
                "access_level": record.access_level,
                "jurisdiction": record.jurisdiction,
                "file_path": record.file_path,
                "tags": record.tags,
                "content_checksum_sha256": record.content_checksum_sha256,
                "index_fingerprint": record.index_fingerprint,
            },
        )
        self.executor.execute(statement)
        return statement

    def delete_document(self, document_id: str) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "DELETE FROM knowledge.knowledge_documents "
                "WHERE document_id = %(document_id)s"
            ),
            params={"document_id": document_id},
        )
        self.executor.execute(statement)
        return statement
