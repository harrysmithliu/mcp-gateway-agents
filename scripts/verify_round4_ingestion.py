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
    api_request = request.Request(
        url=f"{API_BASE_URL.rstrip('/')}/{endpoint_path.lstrip('/')}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with request.urlopen(api_request, timeout=120.0) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        return exc.code, json.loads(response_body) if response_body else {}
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach the API at {API_BASE_URL}.") from exc


def login(username: str) -> str:
    status_code, payload = api_request(
        "POST",
        "/auth/login",
        {"username": username, "password": DEMO_PASSWORD},
    )
    if status_code != 200:
        raise RuntimeError(f"Login failed for {username}: HTTP {status_code}.")
    return str(payload["access_token"])


def expect_status(actual_status: int, expected_status: int, operation: str) -> None:
    if actual_status != expected_status:
        raise RuntimeError(
            f"{operation} returned HTTP {actual_status}, expected {expected_status}."
        )


def main() -> int:
    settings = get_settings()
    sql_plan = build_local_sql_plan(PROJECT_ROOT)
    applied_files = apply_local_sql_plan(
        build_storage_bundle(settings).database_client,
        sql_plan,
    )

    admin_token = login("admin_demo")
    analyst_token = login("analyst_demo")

    status_code, _ = api_request(
        "GET",
        "/admin/knowledge/ingestion-runs?limit=5",
        access_token=analyst_token,
    )
    expect_status(status_code, 403, "analyst ingestion administration access")

    status_code, run_payload = api_request(
        "POST",
        "/admin/knowledge/ingestion-runs",
        access_token=admin_token,
    )
    expect_status(status_code, 200, "admin knowledge refresh")
    run = run_payload.get("run", {})
    run_id = str(run.get("run_id", ""))
    if run.get("status") != "succeeded" or not run_id:
        raise RuntimeError(f"Knowledge refresh did not succeed: {run_payload}")
    count_fields = ("source_count", "document_count", "chunk_count", "embedding_count")
    if not all(run.get(field, 0) > 0 for field in count_fields):
        raise RuntimeError(f"Knowledge refresh returned empty counts: {run_payload}")

    status_code, detail_payload = api_request(
        "GET",
        f"/admin/knowledge/ingestion-runs/{run_id}",
        access_token=admin_token,
    )
    expect_status(status_code, 200, "admin ingestion run detail")
    sources = detail_payload.get("sources", [])
    if len(sources) != run["source_count"]:
        raise RuntimeError("Ingestion run detail did not return the source manifest.")

    status_code, audit_payload = api_request(
        "GET",
        "/audit/recent-events?limit=20&event_type=knowledge_ingestion_succeeded",
        access_token=admin_token,
    )
    expect_status(status_code, 200, "admin ingestion audit review")
    if not any(
        item.get("event_payload", {}).get("run_id") == run_id
        for item in audit_payload.get("events", [])
    ):
        raise RuntimeError("Ingestion success audit event was not found.")

    print(
        json.dumps(
            {
                "api_base_url": API_BASE_URL,
                "applied_sql_file_count": len(applied_files),
                "run_id": run_id,
                "status": run["status"],
                "source_count": run["source_count"],
                "document_count": run["document_count"],
                "chunk_count": run["chunk_count"],
                "embedding_count": run["embedding_count"],
                "authorization_checks": "passed",
                "audit_event": "passed",
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
