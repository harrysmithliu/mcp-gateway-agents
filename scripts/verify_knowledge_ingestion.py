from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.retrieval.persistence import (
    build_retrieval_persistence_service,
    run_default_retrieval_persistence_with_runtime,
)
from backend.storage.bootstrap import apply_local_sql_plan, build_local_sql_plan
from backend.storage.db import DatabaseClient, SQLStatement
from backend.storage.runtime import build_storage_bundle
from backend.storage.settings import get_settings


def query_single_value(
    database_client: DatabaseClient,
    sql: str,
    params: dict[str, object],
) -> int:
    rows = database_client.fetch_all(
        SQLStatement(
            sql=sql,
            params=params,
        )
    )
    if not rows:
        return 0
    first_row = rows[0]
    first_value = next(iter(first_row.values()))
    return int(first_value)


def build_knowledge_persistence_report(
    database_client: DatabaseClient,
    document_ids: tuple[str, ...],
) -> dict[str, int]:
    document_count = 0
    chunk_count = 0
    embedding_count = 0

    for document_id in document_ids:
        document_count += query_single_value(
            database_client,
            (
                "SELECT COUNT(*) FROM knowledge.knowledge_documents "
                "WHERE document_id = %(document_id)s"
            ),
            {"document_id": document_id},
        )
        chunk_count += query_single_value(
            database_client,
            (
                "SELECT COUNT(*) FROM knowledge.knowledge_chunks "
                "WHERE document_id = %(document_id)s"
            ),
            {"document_id": document_id},
        )
        embedding_count += query_single_value(
            database_client,
            (
                "SELECT COUNT(*) "
                "FROM knowledge.chunk_embeddings embedding "
                "JOIN knowledge.knowledge_chunks chunk "
                "ON chunk.chunk_id = embedding.chunk_id "
                "WHERE chunk.document_id = %(document_id)s"
            ),
            {"document_id": document_id},
        )

    return {
        "knowledge_documents": document_count,
        "knowledge_chunks": chunk_count,
        "chunk_embeddings": embedding_count,
    }


def main() -> int:
    settings = get_settings()
    storage_bundle = build_storage_bundle(settings)
    sql_plan = build_local_sql_plan(PROJECT_ROOT)

    try:
        applied_files = apply_local_sql_plan(storage_bundle.database_client, sql_plan)
        service = build_retrieval_persistence_service(storage_bundle)
        run_result = run_default_retrieval_persistence_with_runtime(
            service=service,
            settings=settings,
        )
    except Exception as exc:
        raise RuntimeError(
            "Unable to run default knowledge ingestion. Verify PostgreSQL is running, pgvector is enabled, and DATABASE_URL is reachable."
        ) from exc

    document_ids = tuple(
        {
            chunk_record.source_id
            for chunk_record in run_result.batch_result.chunk_records
        }
    )
    persistence_report = build_knowledge_persistence_report(
        storage_bundle.database_client,
        document_ids=document_ids,
    )

    if (
        persistence_report["knowledge_documents"]
        < run_result.persistence_result.document_count
    ):
        raise RuntimeError("Expected persisted knowledge documents were not found.")
    if persistence_report["knowledge_chunks"] < run_result.persistence_result.chunk_count:
        raise RuntimeError("Expected persisted knowledge chunks were not found.")
    if (
        persistence_report["chunk_embeddings"]
        < run_result.persistence_result.embedding_count
    ):
        raise RuntimeError("Expected persisted chunk embeddings were not found.")

    print(
        json.dumps(
            {
                "database_url": settings.database_url,
                "applied_files": applied_files,
                "document_ids": sorted(document_ids),
                "embedding_provider": settings.embedding_provider,
                "embedding_model_name": run_result.batch_result.embedding_model_name,
                "batch_counts": {
                    "knowledge_documents": run_result.persistence_result.document_count,
                    "knowledge_chunks": run_result.persistence_result.chunk_count,
                    "chunk_embeddings": run_result.persistence_result.embedding_count,
                },
                "postgres_persistence": persistence_report,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
