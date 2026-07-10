import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.models import (
    AgentResponse,
    ChatHistoryMessage,
    PlannedToolCall,
    PlannerResult,
)
from backend.api.mappers import (
    build_chat_command,
    build_chat_response,
    build_tool_invocation_result_response,
)
from backend.api.schemas.chat import ChatRequest
from backend.mcp_gateway.models import ToolInvocationResult
from backend.mcp_gateway.registry import build_default_registry


def test_build_chat_command_maps_recent_messages() -> None:
    request = ChatRequest(
        user_role="analyst",
        message_text="Review this account.",
        session_id="session-r6-001",
        recent_messages=[
            ChatRequest.RecentMessageRequest(
                role="user",
                content="Previous question",
            ),
            ChatRequest.RecentMessageRequest(
                role="assistant",
                content="Previous answer",
            ),
        ],
    )

    command = build_chat_command(request)

    assert command.user_role == "analyst"
    assert command.message_text == "Review this account."
    assert command.session_id == "session-r6-001"
    assert command.recent_messages == [
        ChatHistoryMessage(role="user", content="Previous question"),
        ChatHistoryMessage(role="assistant", content="Previous answer"),
    ]


def test_build_tool_invocation_result_response_maps_registry_result() -> None:
    tool_invocation_result = ToolInvocationResult(
        tool_name="trade.query_metrics",
        domain="trade",
        invocation_status="completed",
        request_payload={"query": "trade wallet volume gamma"},
        response_payload={"total_matches": 1},
    )

    response = build_tool_invocation_result_response(tool_invocation_result)

    assert response.tool_name == "trade.query_metrics"
    assert response.domain == "trade"
    assert response.request_payload["query"] == "trade wallet volume gamma"
    assert response.response_payload["total_matches"] == 1


def test_build_chat_response_adds_registry_notes_and_planner_result() -> None:
    registry = build_default_registry()
    agent_response = AgentResponse(
        reply_text="placeholder",
        session_id="session-r2-001",
        tool_names=["knowledge.search"],
        planned_tool_calls=[
            PlannedToolCall(
                tool_name="knowledge.search",
                domain="knowledge",
                description="Search internal knowledge and return evidence candidates.",
            )
        ],
        tool_invocation_results=[
            ToolInvocationResult(
                tool_name="knowledge.search",
                domain="knowledge",
                invocation_status="completed",
                request_payload={"query": "policy playbook case review"},
                response_payload={"total_matches": 1},
            )
        ],
        evidence=["initial evidence"],
        actions=["draft review"],
        citations=[
            {
                "document_id": "doc-1",
                "title": "Trading Policy",
                "chunk_id": "chunk-1",
                "chunk_index": 2,
                "source_path": "data/trading.md",
                "score": 0.91,
                "excerpt": "Escalate suspicious activity.",
            }
        ],
        planner_result=PlannerResult(
            planner_source="langchain_model",
            raw_output_text="knowledge.search",
            candidate_tool_names=["knowledge.search"],
            selected_tool_names=["knowledge.search"],
            used_fallback=False,
            fallback_reason=None,
        ),
    )

    response = build_chat_response(agent_response, registry)

    assert response.session_id == "session-r2-001"
    assert response.reply_text == "placeholder"
    assert response.tool_names == ["knowledge.search"]
    assert response.evidence[0] == "initial evidence"
    assert any("Matched tool [knowledge]" in note for note in response.evidence)
    assert response.evidence[-1].startswith("Registered MCP tools:")
    assert response.citations[0].chunk_id == "chunk-1"
    assert response.planner_result is not None
    assert response.planner_result.planner_source == "langchain_model"
