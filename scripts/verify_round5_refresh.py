from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.bootstrap import apply_local_sql_plan, build_local_sql_plan
from backend.storage.db import SQLStatement
from backend.storage.runtime import build_storage_bundle
from backend.storage.settings import get_settings


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8000")
DEMO_PASSWORD = "demo-password"


def api_request(
    method: str,
    endpoint_path: str,
    payload: dict[str, object] | None = None,
    access_token: str | None = None,
) -> tuple[int, dict[str, object]]:
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    api_request_value = request.Request(
        url=f"{API_BASE_URL.rstrip('/')}/{endpoint_path.lstrip('/')}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with request.urlopen(api_request_value, timeout=120.0) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        return exc.code, json.loads(response_body) if response_body else {}


def login(username: str) -> str:
    status_code, payload = api_request(
        "POST",
        "/auth/login",
        {"username": username, "password": DEMO_PASSWORD},
    )
    if status_code != 200:
        raise RuntimeError(f"Login failed for {username}: HTTP {status_code}.")
    return str(payload["access_token"])


def expect_status(actual: int, expected: int, operation: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{operation} returned HTTP {actual}, expected {expected}.")


def read_integrity_counts(database_client) -> dict[str, int]:
    queries = {
        "document_count": "SELECT COUNT(*) AS value FROM knowledge.knowledge_documents",
        "chunk_count": "SELECT COUNT(*) AS value FROM knowledge.knowledge_chunks",
        "embedding_count": "SELECT COUNT(*) AS value FROM knowledge.chunk_embeddings",
        "orphan_chunk_count": (
            "SELECT COUNT(*) AS value FROM knowledge.knowledge_chunks AS c "
            "LEFT JOIN knowledge.knowledge_documents AS d ON d.document_id = c.document_id "
            "WHERE d.document_id IS NULL"
        ),
        "orphan_embedding_count": (
            "SELECT COUNT(*) AS value FROM knowledge.chunk_embeddings AS e "
            "LEFT JOIN knowledge.knowledge_chunks AS c ON c.chunk_id = e.chunk_id "
            "WHERE c.chunk_id IS NULL"
        ),
        "invalid_embedding_count": (
            "SELECT COUNT(*) AS value FROM knowledge.chunk_embeddings "
            "WHERE vector_dimensions <> 384 OR vector_dims(embedding) <> 384"
        ),
    }
    counts: dict[str, int] = {}
    for name, sql in queries.items():
        rows = database_client.fetch_all(SQLStatement(sql=sql, params={}))
        counts[name] = int(rows[0]["value"])
    return counts


def main() -> int:
    settings = get_settings()
    sql_plan = build_local_sql_plan(PROJECT_ROOT)
    apply_local_sql_plan(build_storage_bundle(settings).database_client, sql_plan)

    admin_token = login("admin_demo")
    first_status, first_payload = api_request(
        "POST", "/admin/knowledge/ingestion-runs", access_token=admin_token
    )
    expect_status(first_status, 200, "first knowledge refresh")
    first_run = first_payload.get("run", {})
    if first_run.get("status") != "succeeded":
        raise RuntimeError(f"First refresh did not succeed: {first_payload}")

    second_status, second_payload = api_request(
        "POST", "/admin/knowledge/ingestion-runs", access_token=admin_token
    )
    expect_status(second_status, 200, "idempotent knowledge refresh")
    second_run = second_payload.get("run", {})
    second_summary = second_run.get("change_summary", {})
    if second_run.get("status") != "succeeded" or not second_summary.get("no_op"):
        raise RuntimeError(f"Second refresh was not a no-op: {second_payload}")
    for field in (
        "reindexed_source_count",
        "written_document_count",
        "written_chunk_count",
        "written_embedding_count",
        "removed_document_count",
    ):
        if second_summary.get(field, 0) != 0:
            raise RuntimeError(f"No-op refresh wrote data: {second_payload}")

    counts = read_integrity_counts(build_storage_bundle(settings).database_client)
    if counts["document_count"] == 0 or counts["chunk_count"] == 0:
        raise RuntimeError(f"Refresh produced no knowledge data: {counts}")
    if any(
        counts[key] != 0
        for key in (
            "orphan_chunk_count",
            "orphan_embedding_count",
            "invalid_embedding_count",
        )
    ):
        raise RuntimeError(f"Knowledge integrity check failed: {counts}")

    print(
        json.dumps(
            {
                "first_refresh_status": first_run.get("status"),
                "second_refresh_status": second_run.get("status"),
                "second_refresh_no_op": second_summary.get("no_op"),
                "integrity": counts,
                "status": "succeeded",
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
