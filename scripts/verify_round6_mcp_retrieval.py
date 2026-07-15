from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.models import ChatCommand
from backend.api.app import app
from backend.agent.service import AgentService
from backend.mcp_gateway.registry import build_default_registry
from backend.mcp_gateway.transport import build_mcp_transport_router
from backend.retrieval.service import RetrievalService


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8000")
DEMO_PASSWORD = "demo-password"
QUERY = "policy evidence"


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


def extract_http_knowledge_payload(payload: dict[str, object]) -> dict[str, object]:
    response_payload = payload.get("response_payload")
    if not isinstance(response_payload, dict):
        raise RuntimeError(f"HTTP tool returned no response payload: {payload}")
    return response_payload


def extract_agent_knowledge_payload(agent_response) -> dict[str, object]:
    for invocation_result in agent_response.tool_invocation_results:
        if invocation_result.tool_name == "knowledge.search":
            return invocation_result.response_payload
    raise RuntimeError("Agent invocation did not include knowledge.search.")


def semantic_snapshot(payload: dict[str, object]) -> dict[str, object]:
    return {
        "contract_version": payload.get("contract_version"),
        "query": payload.get("query"),
        "result_status": payload.get("result_status"),
        "retrieval_source": payload.get("retrieval_source"),
        "citations": payload.get("citations", []),
    }


def assert_canonical(payload: dict[str, object], source_name: str) -> None:
    if payload.get("contract_version") != "knowledge.search/v1":
        raise RuntimeError(f"{source_name} returned a non-canonical knowledge contract.")
    if payload.get("query") != QUERY:
        raise RuntimeError(f"{source_name} returned the wrong query.")
    if not isinstance(payload.get("citations"), list):
        raise RuntimeError(f"{source_name} returned malformed citations.")
    metadata = payload.get("retrieval_metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError(f"{source_name} returned no retrieval metadata.")
    if metadata.get("status") != payload.get("result_status"):
        raise RuntimeError(f"{source_name} has inconsistent retrieval status.")


def main() -> int:
    analyst_token = login("analyst_demo")
    admin_token = login("admin_demo")

    analyst_status, analyst_http = api_request(
        "POST",
        "/tools/knowledge-search",
        {"query": QUERY, "access_level": "restricted"},
        access_token=analyst_token,
    )
    if analyst_status != 200:
        raise RuntimeError(f"Analyst knowledge request returned HTTP {analyst_status}.")
    analyst_request = analyst_http.get("request_payload", {})
    if "access_level" in analyst_request:
        raise RuntimeError("Client access_level leaked into the analyst request.")
    analyst_context = analyst_request.get("authorization_context", {})
    if analyst_context.get("allowed_access_levels") != ["internal"]:
        raise RuntimeError(f"Unexpected analyst scope: {analyst_context}")
    analyst_http_payload = extract_http_knowledge_payload(analyst_http)

    admin_status, admin_http = api_request(
        "POST",
        "/tools/knowledge-search",
        {"query": QUERY, "access_level": "internal"},
        access_token=admin_token,
    )
    if admin_status != 200:
        raise RuntimeError(f"Admin knowledge request returned HTTP {admin_status}.")
    admin_context = admin_http.get("request_payload", {}).get(
        "authorization_context", {}
    )
    if admin_context.get("allowed_access_levels") != ["internal", "restricted"]:
        raise RuntimeError(f"Unexpected admin scope: {admin_context}")
    admin_http_payload = extract_http_knowledge_payload(admin_http)

    retrieval_service = app.state.container.retrieval_service
    base_registry = build_default_registry(
        retrieval_service=retrieval_service,
    )
    agent_response = AgentService(
        planner_override_output="knowledge.search",
        retrieval_service=retrieval_service,
    ).handle_command(
        ChatCommand(
            user_role="analyst",
            message_text=QUERY,
            authorization_context={
                "access_level": "internal",
                "allowed_access_levels": ["internal"],
            },
        ),
        registry=base_registry,
    )
    agent_payload = extract_agent_knowledge_payload(agent_response)

    sdk_router = build_mcp_transport_router(
        registry=base_registry,
        transport_mode="sdk_stdio",
        server_runtime="runtime",
    )
    sdk_result = sdk_router.invoke(
        tool_name="knowledge.search",
        request_payload={
            "query": QUERY,
            "top_k": 3,
            "authorization_context": {
                "access_level": "internal",
                "allowed_access_levels": ["internal"],
            },
        },
    )
    sdk_payload = sdk_result.response_payload

    for source_name, payload in (
        ("http", analyst_http_payload),
        ("agent", agent_payload),
        ("sdk", sdk_payload),
    ):
        assert_canonical(payload, source_name)
    snapshots = {
        "http": semantic_snapshot(analyst_http_payload),
        "agent": semantic_snapshot(agent_payload),
        "sdk": semantic_snapshot(sdk_payload),
    }
    if not (
        snapshots["http"]["result_status"]
        == snapshots["agent"]["result_status"]
        == snapshots["sdk"]["result_status"]
    ):
        raise RuntimeError(f"Transport result statuses diverged: {snapshots}")
    if not (
        snapshots["http"]["retrieval_source"]
        == snapshots["agent"]["retrieval_source"]
        == snapshots["sdk"]["retrieval_source"]
    ):
        raise RuntimeError(f"Transport retrieval sources diverged: {snapshots}")
    if sdk_result.transport != "sdk_stdio":
        raise RuntimeError("SDK result did not preserve sdk_stdio transport metadata.")
    if "mcp_transport" in sdk_payload:
        raise RuntimeError("SDK transport metadata leaked into semantic payload.")

    disabled_result = build_default_registry(
        retrieval_service=RetrievalService(enabled=False),
    ).invoke("knowledge.search", {"query": QUERY})
    if (
        disabled_result.invocation_status != "unavailable"
        or disabled_result.response_payload.get("result_status") != "disabled"
        or disabled_result.response_payload.get("citations") != []
    ):
        raise RuntimeError("Disabled retrieval did not return the stable unavailable contract.")

    print(
        json.dumps(
            {
                "admin_scope": admin_context.get("allowed_access_levels"),
                "analyst_scope": analyst_context.get("allowed_access_levels"),
                "semantic_snapshots": snapshots,
                "disabled_invocation_status": disabled_result.invocation_status,
                "sdk_transport": sdk_result.transport,
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
