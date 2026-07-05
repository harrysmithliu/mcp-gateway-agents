import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.service import AgentService
from backend.api.app import app
from backend.mcp_gateway.registry import build_default_registry


def test_chat_route_returns_structured_response() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": "Please review trade risk and create an alert.",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert set(payload) == {
        "reply_text",
        "tool_names",
        "planned_tool_calls",
        "tool_invocation_results",
        "evidence",
        "actions",
    }
    assert isinstance(payload["reply_text"], str)
    assert isinstance(payload["tool_names"], list)
    assert isinstance(payload["planned_tool_calls"], list)
    assert isinstance(payload["tool_invocation_results"], list)
    assert isinstance(payload["evidence"], list)
    assert isinstance(payload["actions"], list)

    assert payload["planned_tool_calls"]
    first_planned_tool_call = payload["planned_tool_calls"][0]
    assert set(first_planned_tool_call) == {"tool_name", "domain", "description"}

    assert payload["tool_invocation_results"]
    first_tool_invocation_result = payload["tool_invocation_results"][0]
    assert set(first_tool_invocation_result) == {
        "tool_name",
        "domain",
        "invocation_status",
        "request_payload",
        "response_payload",
    }


def test_chat_route_returns_multiple_tool_invocation_results() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": (
                "Please search the policy playbook, score this borrower account, "
                "query wallet order volume, and create an alert for review."
            ),
        },
    )

    assert response.status_code == 200

    payload = response.json()
    expected_tool_names = [
        "knowledge.search",
        "risk.score_account",
        "trade.query_metrics",
        "ops.create_alert_or_action",
    ]

    assert payload["tool_names"] == expected_tool_names
    assert [item["tool_name"] for item in payload["planned_tool_calls"]] == expected_tool_names
    assert [item["tool_name"] for item in payload["tool_invocation_results"]] == expected_tool_names
    assert all(
        item["invocation_status"] == "completed"
        for item in payload["tool_invocation_results"]
    )


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
        response = client.post(path, json={"query": query})

        assert response.status_code == 200

        payload = response.json()
        assert payload["tool_name"] == expected_tool_name
        assert payload["invocation_status"] == "completed"
        assert payload["request_payload"]["query"] == query
        assert isinstance(payload["response_payload"], dict)


def test_langchain_planner_override_returns_tool_plan() -> None:
    agent_service = AgentService(
        planner_override_output="knowledge.search, trade.query_metrics"
    )
    registry = build_default_registry()

    tool_names, planned_tool_calls, evidence, actions = (
        agent_service.plan_tool_calls_with_langchain(
            normalized_role="analyst",
            normalized_text="Search policy guidance and inspect wallet volume.",
            registry=registry,
        )
    )

    assert tool_names == ["knowledge.search", "trade.query_metrics"]
    assert [item.tool_name for item in planned_tool_calls] == tool_names
    assert "Planner override selected tools before registry-backed execution." in evidence
    assert "RAG-backed citations will be attached after retrieval wiring is implemented." in evidence
    assert actions == []


def test_langchain_planner_payload_includes_output_contract() -> None:
    agent_service = AgentService()
    registry = build_default_registry()

    planner_payload = agent_service.build_langchain_planner_payload(
        normalized_role="analyst",
        normalized_text="Please review trade and risk signals.",
        registry=registry,
    )

    output_contract = planner_payload["output_contract"]

    assert output_contract["format"] == "comma-separated tool names"
    assert output_contract["allow_multiple"] is True
    assert output_contract["fallback_tool"] == "knowledge.search"
    assert output_contract["allowed_tool_names"] == registry.list_tool_names()


def test_langchain_planner_success_takes_priority_over_rule_fallback(monkeypatch) -> None:
    class SuccessfulPlanner:
        def invoke(self, _prompt: str) -> str:
            return "risk.score_account"

    agent_service = AgentService()
    registry = build_default_registry()
    monkeypatch.setattr(
        AgentService,
        "init_langchain_chat_model",
        lambda self: SuccessfulPlanner(),
    )

    tool_names, planned_tool_calls, evidence, actions = (
        agent_service.plan_tool_calls_with_langchain(
            normalized_role="analyst",
            normalized_text="Please search the policy playbook for this case.",
            registry=registry,
        )
    )

    assert tool_names == ["risk.score_account"]
    assert [item.tool_name for item in planned_tool_calls] == tool_names
    assert "LangChain planner selected tools before registry-backed execution." in evidence
    assert (
        "RAG-backed citations will be attached after retrieval wiring is implemented."
        not in evidence
    )
    assert actions == []


def test_langchain_planner_invalid_output_falls_back_to_rule_routing(monkeypatch) -> None:
    class InvalidPlanner:
        def invoke(self, _prompt: str) -> str:
            return "unknown.tool"

    agent_service = AgentService()
    registry = build_default_registry()
    monkeypatch.setattr(
        AgentService,
        "init_langchain_chat_model",
        lambda self: InvalidPlanner(),
    )

    tool_names, planned_tool_calls, evidence, actions = (
        agent_service.plan_tool_calls_with_langchain(
            normalized_role="analyst",
            normalized_text="Please search the policy playbook for this case.",
            registry=registry,
        )
    )

    assert tool_names == ["knowledge.search"]
    assert [item.tool_name for item in planned_tool_calls] == tool_names
    assert "LangChain planner selected tools before registry-backed execution." not in evidence
    assert "RAG-backed citations will be attached after retrieval wiring is implemented." in evidence
    assert actions == []


def test_langchain_planner_empty_output_falls_back_to_rule_routing(monkeypatch) -> None:
    class EmptyPlanner:
        def invoke(self, _prompt: str) -> str:
            return ""

    agent_service = AgentService()
    registry = build_default_registry()
    monkeypatch.setattr(
        AgentService,
        "init_langchain_chat_model",
        lambda self: EmptyPlanner(),
    )

    tool_names, planned_tool_calls, evidence, actions = (
        agent_service.plan_tool_calls_with_langchain(
            normalized_role="analyst",
            normalized_text="Please search the policy playbook for this case.",
            registry=registry,
        )
    )

    assert tool_names == ["knowledge.search"]
    assert [item.tool_name for item in planned_tool_calls] == tool_names
    assert "Planner source: keyword fallback routing." in evidence
    assert "LangChain planner selected tools before registry-backed execution." not in evidence
    assert "RAG-backed citations will be attached after retrieval wiring is implemented." in evidence
    assert actions == []


def test_langchain_planner_falls_back_to_rule_routing(monkeypatch) -> None:
    class FailingPlanner:
        def invoke(self, _prompt: str) -> str:
            raise RuntimeError("planner failed")

    agent_service = AgentService()
    registry = build_default_registry()
    monkeypatch.setattr(
        AgentService,
        "init_langchain_chat_model",
        lambda self: FailingPlanner(),
    )

    tool_names, planned_tool_calls, evidence, actions = (
        agent_service.plan_tool_calls_with_langchain(
            normalized_role="analyst",
            normalized_text="Please search the policy playbook for this case.",
            registry=registry,
        )
    )

    assert tool_names == ["knowledge.search"]
    assert [item.tool_name for item in planned_tool_calls] == tool_names
    assert "RAG-backed citations will be attached after retrieval wiring is implemented." in evidence
    assert actions == []
