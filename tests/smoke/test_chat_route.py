import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.service import AgentService, ChatHistoryMessage
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
        "planner_result",
    }
    assert isinstance(payload["reply_text"], str)
    assert isinstance(payload["tool_names"], list)
    assert isinstance(payload["planned_tool_calls"], list)
    assert isinstance(payload["tool_invocation_results"], list)
    assert isinstance(payload["evidence"], list)
    assert isinstance(payload["actions"], list)
    assert isinstance(payload["planner_result"], dict)

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
    assert set(payload["planner_result"]) == {
        "planner_source",
        "raw_output_text",
        "candidate_tool_names",
        "selected_tool_names",
        "used_fallback",
        "fallback_reason",
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


def test_chat_route_exposes_planner_result(monkeypatch) -> None:
    class InvalidPlanner:
        def invoke(self, _prompt: str) -> str:
            return "unknown.tool"

    client = TestClient(app)
    monkeypatch.setattr(
        AgentService,
        "init_langchain_chat_model",
        lambda self: InvalidPlanner(),
    )

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": "Please search the policy playbook for this case.",
        },
    )

    assert response.status_code == 200

    planner_result = response.json()["planner_result"]
    assert planner_result["planner_source"] == "rule_fallback"
    assert planner_result["raw_output_text"] == "unknown.tool"
    assert planner_result["candidate_tool_names"] == ["unknown.tool"]
    assert planner_result["selected_tool_names"] == ["knowledge.search"]
    assert planner_result["used_fallback"] is True
    assert planner_result["fallback_reason"] == "langchain_output_unusable"


def test_chat_route_forwards_message_history_context(monkeypatch) -> None:
    captured_payload: dict[str, object] = {}
    original_builder = AgentService.build_langchain_message_history_payload

    def capture_message_history_payload(
        self: AgentService,
        session_id: str | None,
        recent_messages: list[ChatHistoryMessage] | None,
        normalized_role: str,
        normalized_text: str,
    ) -> dict[str, object]:
        captured_payload["session_id"] = session_id
        captured_payload["recent_messages"] = recent_messages or []
        captured_payload["normalized_role"] = normalized_role
        captured_payload["normalized_text"] = normalized_text
        return original_builder(
            self,
            session_id=session_id,
            recent_messages=recent_messages,
            normalized_role=normalized_role,
            normalized_text=normalized_text,
        )

    client = TestClient(app)
    monkeypatch.setattr(
        AgentService,
        "build_langchain_message_history_payload",
        capture_message_history_payload,
    )

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": "Review this account with prior context.",
            "session_id": "session-123",
            "recent_messages": [
                {"role": "user", "content": "Previous question"},
                {"role": "assistant", "content": "Previous answer"},
            ],
        },
    )

    assert response.status_code == 200
    assert captured_payload["session_id"] == "session-123"
    assert captured_payload["normalized_role"] == "analyst"
    assert captured_payload["normalized_text"] == "Review this account with prior context."
    recent_messages = captured_payload["recent_messages"]
    assert [message.role for message in recent_messages] == ["user", "assistant"]
    assert [message.content for message in recent_messages] == [
        "Previous question",
        "Previous answer",
    ]


def test_chat_route_closed_loop_with_langchain_contexts(monkeypatch) -> None:
    class SuccessfulPlanner:
        def invoke(self, _prompt: str) -> str:
            return "knowledge.search, ops.create_alert_or_action"

    captured_payload: dict[str, object] = {}
    original_builder = AgentService.build_langchain_planner_payload

    def capture_planner_payload(
        self: AgentService,
        normalized_role: str,
        normalized_text: str,
        registry,
        session_id: str | None = None,
        recent_messages: list[ChatHistoryMessage] | None = None,
    ) -> dict[str, object]:
        planner_payload = original_builder(
            self,
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
            session_id=session_id,
            recent_messages=recent_messages,
        )
        captured_payload.update(planner_payload)
        return planner_payload

    client = TestClient(app)
    monkeypatch.setattr(
        AgentService,
        "init_langchain_chat_model",
        lambda self: SuccessfulPlanner(),
    )
    monkeypatch.setattr(
        AgentService,
        "build_langchain_planner_payload",
        capture_planner_payload,
    )

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": "Please create an alert with policy evidence for this suspicious trade exposure review.",
            "session_id": "session-closed-loop-success",
            "recent_messages": [
                {"role": "user", "content": "Prior question about trade exposure"},
                {"role": "assistant", "content": "Prior answer with review notes"},
            ],
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["planner_result"]["planner_source"] == "langchain_model"
    assert payload["planner_result"]["selected_tool_names"] == [
        "knowledge.search",
        "ops.create_alert_or_action",
    ]
    assert payload["tool_names"] == ["knowledge.search", "ops.create_alert_or_action"]
    assert all(
        item["invocation_status"] == "completed"
        for item in payload["tool_invocation_results"]
    )

    assert captured_payload["output_contract"]["fallback_tool"] == "knowledge.search"
    assert captured_payload["message_history"]["session_id"] == "session-closed-loop-success"
    assert len(captured_payload["message_history"]["messages"]) == 3
    assert captured_payload["retrieval_context"]["rag_enabled"] is True
    assert captured_payload["retrieval_context"]["retrieved_chunks"]
    assert "ops_action_requested" in captured_payload["guardrail_context"]["input_checks"]
    assert captured_payload["guardrail_context"]["escalation_required"] is True
    assert (
        "do_not_execute_privileged_ops_actions"
        in captured_payload["guardrail_context"]["output_constraints"]
    )


def test_chat_route_closed_loop_fallback_preserves_context(monkeypatch) -> None:
    class InvalidPlanner:
        def invoke(self, _prompt: str) -> str:
            return "unknown.tool"

    captured_payload: dict[str, object] = {}
    original_builder = AgentService.build_langchain_planner_payload

    def capture_planner_payload(
        self: AgentService,
        normalized_role: str,
        normalized_text: str,
        registry,
        session_id: str | None = None,
        recent_messages: list[ChatHistoryMessage] | None = None,
    ) -> dict[str, object]:
        planner_payload = original_builder(
            self,
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
            session_id=session_id,
            recent_messages=recent_messages,
        )
        captured_payload.update(planner_payload)
        return planner_payload

    client = TestClient(app)
    monkeypatch.setattr(
        AgentService,
        "init_langchain_chat_model",
        lambda self: InvalidPlanner(),
    )
    monkeypatch.setattr(
        AgentService,
        "build_langchain_planner_payload",
        capture_planner_payload,
    )

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": "Please create an alert with policy evidence for this suspicious trade exposure review.",
            "session_id": "session-closed-loop-fallback",
            "recent_messages": [
                {"role": "user", "content": "Prior question about trade exposure"},
                {"role": "assistant", "content": "Prior answer with review notes"},
            ],
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["planner_result"]["planner_source"] == "rule_fallback"
    assert payload["planner_result"]["fallback_reason"] == "langchain_output_unusable"
    assert payload["planner_result"]["selected_tool_names"] == [
        "knowledge.search",
        "trade.query_metrics",
        "ops.create_alert_or_action",
    ]
    assert payload["tool_names"] == [
        "knowledge.search",
        "trade.query_metrics",
        "ops.create_alert_or_action",
    ]
    assert all(
        item["invocation_status"] == "completed"
        for item in payload["tool_invocation_results"]
    )

    assert captured_payload["message_history"]["session_id"] == "session-closed-loop-fallback"
    assert captured_payload["retrieval_context"]["rag_enabled"] is True
    assert captured_payload["guardrail_context"]["escalation_required"] is True
    assert captured_payload["planner_prompt"]


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

    tool_names, planned_tool_calls, evidence, actions, planner_result = (
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
    assert planner_result.planner_source == "planner_override"
    assert planner_result.used_fallback is False


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


def test_langchain_planner_payload_includes_request_message_history() -> None:
    agent_service = AgentService()
    registry = build_default_registry()

    planner_payload = agent_service.build_langchain_planner_payload(
        normalized_role="analyst",
        normalized_text="Please review trade and risk signals.",
        registry=registry,
        session_id="session-456",
        recent_messages=[
            ChatHistoryMessage(role="user", content="Previous analyst question"),
            ChatHistoryMessage(role="assistant", content="Previous assistant answer"),
        ],
    )

    message_history = planner_payload["message_history"]
    assert message_history["session_id"] == "session-456"
    assert message_history["history_source"] == "request_messages"
    assert message_history["messages"] == [
        {"role": "user", "content": "Previous analyst question"},
        {"role": "assistant", "content": "Previous assistant answer"},
        {
            "role": "user",
            "content": "Please review trade and risk signals.",
            "actor_role": "analyst",
        },
    ]


def test_langchain_planner_payload_includes_retrieval_context_matches() -> None:
    agent_service = AgentService()
    registry = build_default_registry()

    planner_payload = agent_service.build_langchain_planner_payload(
        normalized_role="analyst",
        normalized_text="Search policy evidence for suspicious trade exposure.",
        registry=registry,
    )

    retrieval_context = planner_payload["retrieval_context"]
    assert retrieval_context["rag_enabled"] is True
    assert retrieval_context["retrieval_source"] == "knowledge_preview"
    assert retrieval_context["retrieved_chunks"]
    assert retrieval_context["citations"]
    first_chunk = retrieval_context["retrieved_chunks"][0]
    assert set(first_chunk) == {"document_id", "title", "summary", "matched_terms"}


def test_langchain_planner_prompt_includes_retrieval_context_summary() -> None:
    agent_service = AgentService()
    registry = build_default_registry()

    retrieval_context = agent_service.build_langchain_retrieval_context_payload(
        normalized_text="Search policy evidence for suspicious trade exposure.",
        registry=registry,
    )
    planner_prompt = agent_service.build_langchain_planner_prompt(
        normalized_role="analyst",
        normalized_text="Search policy evidence for suspicious trade exposure.",
        registry=registry,
        retrieval_context=retrieval_context,
        guardrail_context=agent_service.build_langchain_guardrail_context_payload(
            normalized_role="analyst",
            normalized_text="Search policy evidence for suspicious trade exposure.",
        ),
    )

    assert "Retrieval context:" in planner_prompt
    assert "Risk Escalation Policy" in planner_prompt or "Trade Risk Review Playbook" in planner_prompt


def test_langchain_planner_payload_includes_guardrail_context_constraints() -> None:
    agent_service = AgentService()
    registry = build_default_registry()

    planner_payload = agent_service.build_langchain_planner_payload(
        normalized_role="analyst",
        normalized_text="Please freeze this account and create an alert.",
        registry=registry,
    )

    guardrail_context = planner_payload["guardrail_context"]
    assert guardrail_context["user_role"] == "analyst"
    assert guardrail_context["allowed_action_scope"] == "analysis_only"
    assert guardrail_context["escalation_required"] is True
    assert "sensitive_action_requested" in guardrail_context["input_checks"]
    assert "ops_action_requested" in guardrail_context["input_checks"]
    assert "do_not_initiate_sensitive_actions" in guardrail_context["output_constraints"]
    assert "do_not_execute_privileged_ops_actions" in guardrail_context["output_constraints"]


def test_langchain_planner_prompt_includes_guardrail_context_summary() -> None:
    agent_service = AgentService()
    registry = build_default_registry()

    retrieval_context = agent_service.build_langchain_retrieval_context_payload(
        normalized_text="Please freeze this account and create an alert.",
        registry=registry,
    )
    guardrail_context = agent_service.build_langchain_guardrail_context_payload(
        normalized_role="analyst",
        normalized_text="Please freeze this account and create an alert.",
    )
    planner_prompt = agent_service.build_langchain_planner_prompt(
        normalized_role="analyst",
        normalized_text="Please freeze this account and create an alert.",
        registry=registry,
        retrieval_context=retrieval_context,
        guardrail_context=guardrail_context,
    )

    assert "Guardrail context:" in planner_prompt
    assert "scope=analysis_only" in planner_prompt
    assert "sensitive_action_requested" in planner_prompt
    assert "ops_action_requested" in planner_prompt


def test_langchain_planner_override_filters_to_allowed_tools_with_stable_order() -> None:
    agent_service = AgentService(
        planner_override_output=(
            "TRADE.QUERY_METRICS, unknown.tool, risk.score_account, trade.query_metrics"
        )
    )
    registry = build_default_registry()

    tool_names, planned_tool_calls, evidence, actions, planner_result = (
        agent_service.plan_tool_calls_with_langchain(
            normalized_role="analyst",
            normalized_text="Review wallet activity and account risk.",
            registry=registry,
        )
    )

    assert tool_names == ["trade.query_metrics", "risk.score_account"]
    assert [item.tool_name for item in planned_tool_calls] == tool_names
    assert "Planner source: override output." in evidence
    assert "Planner override selected tools before registry-backed execution." in evidence
    assert actions == []
    assert planner_result.selected_tool_names == tool_names
    assert planner_result.candidate_tool_names == [
        "TRADE.QUERY_METRICS",
        "unknown.tool",
        "risk.score_account",
        "trade.query_metrics",
    ]


def test_langchain_planner_result_tracks_fallback_reason_and_raw_output(monkeypatch) -> None:
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

    planner_result = agent_service.build_langchain_planner_result(
        normalized_role="analyst",
        normalized_text="Please search the policy playbook for this case.",
        registry=registry,
    )

    assert planner_result.planner_source == "rule_fallback"
    assert planner_result.raw_output_text == "unknown.tool"
    assert planner_result.candidate_tool_names == ["unknown.tool"]
    assert planner_result.selected_tool_names == ["knowledge.search"]
    assert planner_result.used_fallback is True
    assert planner_result.fallback_reason == "langchain_output_unusable"


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

    tool_names, planned_tool_calls, evidence, actions, planner_result = (
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
    assert planner_result.planner_source == "langchain_model"
    assert planner_result.used_fallback is False


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

    tool_names, planned_tool_calls, evidence, actions, planner_result = (
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
    assert planner_result.planner_source == "rule_fallback"
    assert planner_result.fallback_reason == "langchain_output_unusable"


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

    tool_names, planned_tool_calls, evidence, actions, planner_result = (
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
    assert planner_result.planner_source == "rule_fallback"
    assert planner_result.fallback_reason == "langchain_output_unusable"


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

    tool_names, planned_tool_calls, evidence, actions, planner_result = (
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
    assert planner_result.planner_source == "rule_fallback"
    assert planner_result.fallback_reason == "planner_invoke_failed"
