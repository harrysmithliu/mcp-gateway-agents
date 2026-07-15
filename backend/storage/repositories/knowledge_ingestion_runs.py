from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import (
    KnowledgeIngestionRunRecord,
    KnowledgeIngestionSourceRecord,
)
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class KnowledgeIngestionRunRepository:
    executor: StatementExecutor

    def has_running_run(self) -> bool:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT run_id FROM knowledge.ingestion_runs "
                    "WHERE status = 'running' LIMIT 1"
                ),
                params={},
            )
        )
        return bool(rows)

    def create_run(self, record: KnowledgeIngestionRunRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO knowledge.ingestion_runs "
                "(run_id, requested_by_user_id, run_mode, status, source_count, "
                "document_count, chunk_count, embedding_count, embedding_provider, "
                "embedding_model_name, vector_dimensions, error_type, error_summary, "
                "change_summary, started_at) "
                "VALUES ("
                "%(run_id)s, %(requested_by_user_id)s, %(run_mode)s, %(status)s, "
                "%(source_count)s, %(document_count)s, %(chunk_count)s, "
                "%(embedding_count)s, %(embedding_provider)s, %(embedding_model_name)s, "
                "%(vector_dimensions)s, %(error_type)s, %(error_summary)s, "
                "%(change_summary)s, NOW()"
                ")"
            ),
            params={
                "run_id": record.run_id,
                "requested_by_user_id": record.requested_by_user_id,
                "run_mode": record.run_mode,
                "status": record.status,
                "source_count": record.source_count,
                "document_count": record.document_count,
                "chunk_count": record.chunk_count,
                "embedding_count": record.embedding_count,
                "embedding_provider": record.embedding_provider,
                "embedding_model_name": record.embedding_model_name,
                "vector_dimensions": record.vector_dimensions,
                "error_type": record.error_type,
                "error_summary": record.error_summary,
                "change_summary": record.change_summary,
            },
        )
        self.executor.execute(statement)
        return statement

    def create_source(self, record: KnowledgeIngestionSourceRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO knowledge.ingestion_run_sources "
                "(run_id, source_id, title, source_path, checksum_sha256, byte_size, "
                "content_type, access_level, jurisdiction, tags, index_fingerprint) "
                "VALUES ("
                "%(run_id)s, %(source_id)s, %(title)s, %(source_path)s, "
                "%(checksum_sha256)s, %(byte_size)s, %(content_type)s, "
                "%(access_level)s, %(jurisdiction)s, %(tags)s, "
                "%(index_fingerprint)s"
                ")"
            ),
            params={
                "run_id": record.run_id,
                "source_id": record.source_id,
                "title": record.title,
                "source_path": record.source_path,
                "checksum_sha256": record.checksum_sha256,
                "byte_size": record.byte_size,
                "content_type": record.content_type,
                "access_level": record.access_level,
                "jurisdiction": record.jurisdiction,
                "tags": record.tags,
                "index_fingerprint": record.index_fingerprint,
            },
        )
        self.executor.execute(statement)
        return statement

    def mark_succeeded(
        self,
        run_id: str,
        source_count: int,
        document_count: int,
        chunk_count: int,
        embedding_count: int,
        embedding_provider: str | None,
        embedding_model_name: str | None,
        vector_dimensions: int | None,
        change_summary: dict[str, object] | None = None,
    ) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "UPDATE knowledge.ingestion_runs SET status = 'succeeded', "
                "source_count = %(source_count)s, document_count = %(document_count)s, "
                "chunk_count = %(chunk_count)s, embedding_count = %(embedding_count)s, "
                "embedding_provider = %(embedding_provider)s, "
                "embedding_model_name = %(embedding_model_name)s, "
                "vector_dimensions = %(vector_dimensions)s, "
                "change_summary = %(change_summary)s, completed_at = NOW() "
                "WHERE run_id = %(run_id)s AND status = 'running'"
            ),
            params={
                "run_id": run_id,
                "source_count": source_count,
                "document_count": document_count,
                "chunk_count": chunk_count,
                "embedding_count": embedding_count,
                "embedding_provider": embedding_provider,
                "embedding_model_name": embedding_model_name,
                "vector_dimensions": vector_dimensions,
                "change_summary": change_summary or {},
            },
        )
        self.executor.execute(statement)
        return statement

    def mark_failed(
        self,
        run_id: str,
        error_type: str,
        error_summary: str,
    ) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "UPDATE knowledge.ingestion_runs SET status = 'failed', "
                "error_type = %(error_type)s, error_summary = %(error_summary)s, "
                "completed_at = NOW() "
                "WHERE run_id = %(run_id)s AND status = 'running'"
            ),
            params={
                "run_id": run_id,
                "error_type": error_type,
                "error_summary": error_summary,
            },
        )
        self.executor.execute(statement)
        return statement

    def list_recent_runs(self, limit: int = 20) -> list[dict[str, object]]:
        return self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT run_id, requested_by_user_id, run_mode, status, "
                    "source_count, document_count, chunk_count, embedding_count, "
                    "embedding_provider, embedding_model_name, vector_dimensions, "
                    "error_type, error_summary, change_summary, started_at, "
                    "completed_at, created_at "
                    "FROM knowledge.ingestion_runs "
                    "ORDER BY created_at DESC LIMIT %(limit)s"
                ),
                params={"limit": limit},
            )
        )

    def get_run(self, run_id: str) -> dict[str, object] | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT run_id, requested_by_user_id, run_mode, status, "
                    "source_count, document_count, chunk_count, embedding_count, "
                    "embedding_provider, embedding_model_name, vector_dimensions, "
                    "error_type, error_summary, change_summary, started_at, "
                    "completed_at, created_at "
                    "FROM knowledge.ingestion_runs WHERE run_id = %(run_id)s"
                ),
                params={"run_id": run_id},
            )
        )
        return rows[0] if rows else None

    def get_latest_succeeded_run(self) -> dict[str, object] | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT run_id, requested_by_user_id, run_mode, status, "
                    "source_count, document_count, chunk_count, embedding_count, "
                    "embedding_provider, embedding_model_name, vector_dimensions, "
                    "error_type, error_summary, change_summary, started_at, "
                    "completed_at, created_at "
                    "FROM knowledge.ingestion_runs "
                    "WHERE status = 'succeeded' "
                    "ORDER BY completed_at DESC NULLS LAST, created_at DESC LIMIT 1"
                ),
                params={},
            )
        )
        return rows[0] if rows else None

    def list_sources(self, run_id: str) -> list[dict[str, object]]:
        return self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT run_id, source_id, title, source_path, checksum_sha256, "
                    "byte_size, content_type, access_level, jurisdiction, tags, "
                    "index_fingerprint, created_at "
                    "FROM knowledge.ingestion_run_sources "
                    "WHERE run_id = %(run_id)s ORDER BY source_id"
                ),
                params={"run_id": run_id},
            )
        )
