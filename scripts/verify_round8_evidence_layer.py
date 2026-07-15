from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.models import ChatCommand
from backend.agent.service import AgentService
from backend.mcp_gateway.registry import build_default_registry
from backend.mcp_gateway.transport import build_mcp_transport_router
from backend.retrieval.service import RetrievalService
from backend.storage.bootstrap import apply_local_sql_plan, build_local_sql_plan
from backend.storage.db import SQLStatement
from backend.storage.runtime import build_storage_bundle
from backend.storage.settings import get_settings


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8000")
FRONTEND_BASE_URL = os.getenv("VERIFY_FRONTEND_URL", "http://127.0.0.1:8501")
DEMO_PASSWORD = "demo-password"
KNOWLEDGE_QUERY = "policy evidence"
CHAT_QUERY = "Find the trading surveillance policy and cite the supporting evidence."


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
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach the API at {API_BASE_URL}.") from exc


def expect_status(actual: int, expected: int, operation: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{operation} returned HTTP {actual}, expected {expected}.")


def login(username: str) -> str:
    status_code, payload = api_request(
        "POST",
        "/auth/login",
        {"username": username, "password": DEMO_PASSWORD},
    )
    expect_status(status_code, 200, f"login for {username}")
    return str(payload["access_token"])


def check_readiness() -> dict[str, object]:
    status_code, health_payload = api_request("GET", "/health")
    expect_status(status_code, 200, "backend health")
    retrieval = health_payload.get("retrieval")
    if health_payload.get("status") != "ok" or not isinstance(retrieval, dict):
        raise RuntimeError(f"Backend health is not ready: {health_payload}")
    if retrieval.get("state") != "ready":
        raise RuntimeError(f"Retrieval runtime is not ready: {retrieval}")

    try:
        with request.urlopen(FRONTEND_BASE_URL, timeout=30.0) as response:
            frontend_status = response.status
    except (error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Unable to reach the frontend at {FRONTEND_BASE_URL}."
        ) from exc
    if frontend_status != 200:
        raise RuntimeError(f"Frontend returned HTTP {frontend_status}.")

    settings = get_settings()
    try:
        import redis

        redis_client = redis.Redis.from_url(settings.redis_url)
        redis_ready = bool(redis_client.ping())
    except Exception as exc:
        raise RuntimeError("Redis readiness check failed.") from exc
    finally:
        if "redis_client" in locals():
            redis_client.close()
    if not redis_ready:
        raise RuntimeError("Redis ping did not return a healthy response.")

    applied_files = apply_local_sql_plan(
        build_storage_bundle(settings).database_client,
        build_local_sql_plan(PROJECT_ROOT),
    )
    return {
        "backend_health": health_payload,
        "frontend_status": frontend_status,
        "redis_status": "passed",
        "applied_sql_file_count": len(applied_files),
    }


def read_persisted_counts() -> dict[str, int]:
    database_client = build_storage_bundle(get_settings()).database_client
    rows = database_client.fetch_all(
        SQLStatement(
            sql=(
                "SELECT "
                "(SELECT count(*) FROM knowledge.knowledge_documents) AS documents, "
                "(SELECT count(*) FROM knowledge.knowledge_chunks) AS chunks, "
                "(SELECT count(*) FROM knowledge.chunk_embeddings) AS embeddings"
            ),
            params={},
        )
    )
    counts = rows[0]
    result = {
        "documents": int(counts["documents"]),
        "chunks": int(counts["chunks"]),
        "embeddings": int(counts["embeddings"]),
    }
    return result


def ensure_persisted_embeddings() -> dict[str, object]:
    counts = read_persisted_counts()
    if all(value > 0 for value in counts.values()):
        return {"status": "ready", "counts": counts}

    from scripts.verify_knowledge_ingestion import main as verify_ingestion

    captured_output = io.StringIO()
    with contextlib.redirect_stdout(captured_output):
        result = verify_ingestion()
    if result != 0:
        raise RuntimeError("Controlled knowledge ingestion recovery failed.")

    recovered_counts = read_persisted_counts()
    if not all(value > 0 for value in recovered_counts.values()):
        raise RuntimeError(
            f"Knowledge ingestion recovery left incomplete counts: {recovered_counts}"
        )
    return {
        "status": "recovered",
        "before": counts,
        "after": recovered_counts,
    }


def run_admin_refresh(admin_token: str) -> dict[str, object]:
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

    status_code, detail_payload = api_request(
        "GET",
        f"/admin/knowledge/ingestion-runs/{run_id}",
        access_token=admin_token,
    )
    expect_status(status_code, 200, "admin ingestion run detail")
    sources = detail_payload.get("sources", [])
    if len(sources) != run.get("source_count"):
        raise RuntimeError("Ingestion detail does not match source manifest count.")

    status_code, audit_payload = api_request(
        "GET",
        "/audit/recent-events?limit=20&event_type=knowledge_ingestion_succeeded",
        access_token=admin_token,
    )
    expect_status(status_code, 200, "knowledge ingestion audit review")
    if not any(
        item.get("event_payload", {}).get("run_id") == run_id
        for item in audit_payload.get("events", [])
    ):
        raise RuntimeError("Knowledge ingestion success audit event was not found.")

    return {
        "run_id": run_id,
        "status": run["status"],
        "source_count": run.get("source_count", 0),
        "document_count": run.get("document_count", 0),
        "chunk_count": run.get("chunk_count", 0),
        "embedding_count": run.get("embedding_count", 0),
        "audit_event": "passed",
    }


def _assert_citation(citation: object) -> None:
    if not isinstance(citation, dict):
        raise RuntimeError("Citation is not an object.")
    required_fields = ("document_id", "title", "chunk_id", "chunk_index", "excerpt")
    if any(citation.get(field) in (None, "") for field in required_fields):
        raise RuntimeError(f"Citation is missing required evidence fields: {citation}")


def run_evidence_workflow(analyst_token: str) -> dict[str, object]:
    status_code, tool_response = api_request(
        "POST",
        "/tools/knowledge-search",
        {
            "query": KNOWLEDGE_QUERY,
            "access_level": "restricted",
            "top_k": 3,
        },
        access_token=analyst_token,
    )
    expect_status(status_code, 200, "analyst knowledge search")
    request_payload = tool_response.get("request_payload", {})
    authorization_context = request_payload.get("authorization_context", {})
    if authorization_context.get("allowed_access_levels") != ["internal"]:
        raise RuntimeError(f"Analyst scope was not server-owned: {request_payload}")
    if "access_level" in request_payload:
        raise RuntimeError("Client access_level leaked into the tool request.")
    response_payload = tool_response.get("response_payload", {})
    if response_payload.get("result_status") != "completed":
        raise RuntimeError(f"Analyst retrieval was not completed: {response_payload}")
    citations = response_payload.get("citations", [])
    if not isinstance(citations, list) or not citations:
        raise RuntimeError("Analyst knowledge search returned no citations.")
    for citation in citations:
        _assert_citation(citation)

    status_code, chat_payload = api_request(
        "POST",
        "/chat",
        {"message_text": CHAT_QUERY, "user_role": "analyst"},
        access_token=analyst_token,
    )
    expect_status(status_code, 200, "analyst evidence chat")
    if "knowledge.search" not in chat_payload.get("tool_names", []):
        raise RuntimeError(f"Chat did not select knowledge.search: {chat_payload}")
    chat_citations = chat_payload.get("citations", [])
    if not isinstance(chat_citations, list) or not chat_citations:
        raise RuntimeError("Evidence chat returned no citations.")
    for citation in chat_citations:
        _assert_citation(citation)

    return {
        "knowledge_search_status": response_payload.get("result_status"),
        "knowledge_citation_count": len(citations),
        "chat_tool_names": chat_payload.get("tool_names", []),
        "chat_citation_count": len(chat_citations),
        "citation_schema": "passed",
    }


def run_transport_parity() -> dict[str, object]:
    from scripts.verify_round6_mcp_retrieval import main as verify_round6

    captured_output = io.StringIO()
    with contextlib.redirect_stdout(captured_output):
        result = verify_round6()
    if result != 0:
        raise RuntimeError("Round 6 retrieval parity verifier failed.")
    try:
        parity_summary = json.loads(captured_output.getvalue())
    except json.JSONDecodeError as exc:
        raise RuntimeError("Parity verifier did not return JSON output.") from exc
    if parity_summary.get("status") != "succeeded":
        raise RuntimeError(f"Parity verifier returned an invalid summary: {parity_summary}")
    return {
        "status": parity_summary["status"],
        "analyst_scope": parity_summary.get("analyst_scope"),
        "admin_scope": parity_summary.get("admin_scope"),
        "sdk_transport": parity_summary.get("sdk_transport"),
        "disabled_invocation_status": parity_summary.get(
            "disabled_invocation_status"
        ),
    }


def run_disabled_contract() -> dict[str, object]:
    disabled_retrieval = RetrievalService(enabled=False)
    registry = build_default_registry(retrieval_service=disabled_retrieval)
    disabled_result = registry.invoke(
        "knowledge.search",
        {"query": KNOWLEDGE_QUERY},
    )
    if (
        disabled_result.invocation_status != "unavailable"
        or disabled_result.response_payload.get("result_status") != "disabled"
        or disabled_result.response_payload.get("citations") != []
    ):
        raise RuntimeError("Disabled registry contract is unstable.")

    trade_response = AgentService(
        retrieval_service=disabled_retrieval,
    ).handle_command(
        ChatCommand(
            user_role="analyst",
            message_text="Query the trading volume for Gamma.",
        ),
        registry=registry,
    )
    if not any(
        result.tool_name == "trade.query_metrics"
        and result.invocation_status == "completed"
        for result in trade_response.tool_invocation_results
    ):
        raise RuntimeError("Non-retrieval trade workflow failed while RAG was disabled.")

    previous_retrieval_enabled = os.environ.get("RETRIEVAL_ENABLED")
    os.environ["RETRIEVAL_ENABLED"] = "false"
    try:
        sdk_router = build_mcp_transport_router(
            registry=registry,
            transport_mode="sdk_stdio",
            server_runtime="runtime",
        )
        sdk_result = sdk_router.invoke(
            "knowledge.search",
            {"query": KNOWLEDGE_QUERY},
        )
    finally:
        if previous_retrieval_enabled is None:
            os.environ.pop("RETRIEVAL_ENABLED", None)
        else:
            os.environ["RETRIEVAL_ENABLED"] = previous_retrieval_enabled
    if (
        sdk_result.invocation_status != "unavailable"
        or sdk_result.response_payload.get("result_status") != "disabled"
    ):
        raise RuntimeError("Disabled MCP retrieval contract is unstable.")

    return {
        "registry_status": disabled_result.response_payload.get("result_status"),
        "mcp_status": sdk_result.response_payload.get("result_status"),
        "non_retrieval_trade": "passed",
    }


def main() -> int:
    readiness = check_readiness()
    admin_token = login("admin_demo")
    analyst_token = login("analyst_demo")
    refresh = run_admin_refresh(admin_token)
    persisted_embedding_state = ensure_persisted_embeddings()
    persisted_counts = persisted_embedding_state["counts"] if persisted_embedding_state["status"] == "ready" else persisted_embedding_state["after"]
    evidence = run_evidence_workflow(analyst_token)
    parity = run_transport_parity()
    disabled = run_disabled_contract()
    print(
        json.dumps(
            {
                "api_base_url": API_BASE_URL,
                "frontend_base_url": FRONTEND_BASE_URL,
                "readiness": readiness,
                "refresh": refresh,
                "persisted_counts": persisted_counts,
                "persisted_embedding_state": persisted_embedding_state,
                "evidence_workflow": evidence,
                "transport_parity": parity,
                "disabled_closure": disabled,
                "status": "succeeded",
                "token_cost": "none",
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
