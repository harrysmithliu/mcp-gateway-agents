import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_tool_routes_return_completed_invocation_results() -> None:
    client = TestClient(app)

    tool_requests = [
        ("/tools/knowledge-search", "policy playbook case review", "knowledge.search"),
        ("/tools/risk-score-account", "risk borrower account atlas score", "risk.score_account"),
        ("/tools/trade-query-metrics", "trade wallet volume gamma", "trade.query_metrics"),
        (
            "/tools/ops-create-alert-or-action",
            "alert escalate suspicious risk review",
            "ops.create_alert_or_action",
        ),
    ]

    for path, query, expected_tool_name in tool_requests:
        headers = (
            {"x-demo-user": "risk_operator_demo"}
            if expected_tool_name == "ops.create_alert_or_action"
            else {}
        )
        response = client.post(path, json={"query": query}, headers=headers)

        assert response.status_code == 200

        payload = response.json()
        assert payload["tool_name"] == expected_tool_name
        assert payload["invocation_status"] == "completed"
        assert payload["request_payload"]["query"] == query
        assert isinstance(payload["response_payload"], dict)


def test_knowledge_http_route_ignores_client_access_override() -> None:
    client = TestClient(app)

    response = client.post(
        "/tools/knowledge-search",
        json={
            "query": "policy evidence",
            "access_level": "restricted",
        },
    )

    assert response.status_code == 200
    request_payload = response.json()["request_payload"]
    assert "access_level" not in request_payload
    assert request_payload["authorization_context"]["allowed_access_levels"] == [
        "internal"
    ]
    response_payload = response.json()["response_payload"]
    assert response_payload["contract_version"] == "knowledge.search/v1"
    assert isinstance(response_payload["citations"], list)


def test_knowledge_http_route_derives_hierarchical_scope_for_admin() -> None:
    client = TestClient(app)

    response = client.post(
        "/tools/knowledge-search",
        json={"query": "restricted policy", "access_level": "internal"},
        headers={"x-demo-user": "admin_demo"},
    )

    assert response.status_code == 200
    request_payload = response.json()["request_payload"]
    assert "access_level" not in request_payload
    assert request_payload["authorization_context"]["allowed_access_levels"] == [
        "internal",
        "restricted",
    ]
    response_payload = response.json()["response_payload"]
    assert response_payload["contract_version"] == "knowledge.search/v1"
