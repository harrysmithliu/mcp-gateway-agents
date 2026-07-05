import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.service import AgentService, ChatHistoryMessage
from backend.api.app import app


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
