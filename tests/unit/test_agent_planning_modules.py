import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.models import ChatHistoryMessage
from backend.agent.planning.langchain import build_planner_source_evidence
from backend.agent.planning.parser import (
    extract_langchain_planner_output_candidates,
    parse_langchain_planner_output,
)
from backend.agent.planning.prompt import (
    LangChainPlannerConfig,
    build_langchain_message_history_payload,
    build_langchain_planner_payload,
    build_langchain_planner_prompt,
)


def test_parser_extracts_normalized_candidates_from_free_text() -> None:
    candidates = extract_langchain_planner_output_candidates(
        " knowledge.search ; `risk.score_account` | unknown.tool "
    )

    assert candidates == [
        "knowledge.search",
        "risk.score_account",
        "unknown.tool",
    ]


def test_parser_filters_to_allowed_tools_with_stable_order() -> None:
    selected_tool_names = parse_langchain_planner_output(
        planner_output_text=(
            "TRADE.QUERY_METRICS, unknown.tool, risk.score_account, trade.query_metrics"
        ),
        allowed_tool_names=[
            "knowledge.search",
            "risk.score_account",
            "trade.query_metrics",
        ],
    )

    assert selected_tool_names == [
        "trade.query_metrics",
        "risk.score_account",
    ]


def test_prompt_builders_preserve_message_history_and_context_fields() -> None:
    planner_config = LangChainPlannerConfig(
        package_name="langchain",
        model_provider="anthropic",
        model_name="claude-haiku-4-5",
        planner_mode="tool-routing-placeholder",
    )
    message_history = build_langchain_message_history_payload(
        session_id="session-r3-001",
        recent_messages=[
            ChatHistoryMessage(role="user", content="Previous question"),
            ChatHistoryMessage(role="assistant", content="Previous answer"),
        ],
        normalized_role="analyst",
        normalized_text="Review this suspicious trade exposure.",
    )
    planner_payload = build_langchain_planner_payload(
        normalized_role="analyst",
        normalized_text="Review this suspicious trade exposure.",
        planner_config=planner_config,
        tool_catalog=[
            {
                "tool_name": "knowledge.search",
                "domain": "knowledge",
                "description": "Search internal knowledge and return evidence candidates.",
            }
        ],
        output_contract={
            "format": "comma-separated tool names",
            "allow_multiple": True,
            "allowed_tool_names": ["knowledge.search"],
            "fallback_tool": "knowledge.search",
        },
        message_history=message_history,
        retrieval_context={
            "rag_enabled": True,
            "retrieval_source": "knowledge_preview",
            "retrieved_chunks": [
                {
                    "document_id": "doc-001",
                    "title": "Risk Escalation Policy",
                    "summary": "Escalate high-risk trade reviews.",
                    "matched_terms": ["risk", "trade"],
                }
            ],
            "citations": [{"document_id": "doc-001", "title": "Risk Escalation Policy"}],
        },
        guardrail_context={
            "user_role": "analyst",
            "input_checks": ["ops_action_requested"],
            "output_constraints": ["limit_response_to_draft_or_summary"],
            "allowed_action_scope": "analysis_only",
            "escalation_required": True,
        },
    )

    assert planner_payload["message_history"]["session_id"] == "session-r3-001"
    assert len(planner_payload["message_history"]["messages"]) == 3
    assert planner_payload["retrieval_context"]["rag_enabled"] is True
    assert planner_payload["guardrail_context"]["escalation_required"] is True
    assert "Risk Escalation Policy" in planner_payload["planner_prompt"]
    assert "scope=analysis_only" in planner_payload["planner_prompt"]


def test_build_planner_source_evidence_returns_known_label() -> None:
    assert (
        build_planner_source_evidence("langchain_model")
        == "Planner source: LangChain model output."
    )


def test_build_langchain_planner_prompt_embeds_contract_and_context() -> None:
    planner_prompt = build_langchain_planner_prompt(
        normalized_role="analyst",
        normalized_text="Search policy evidence.",
        output_contract={
            "format": "comma-separated tool names",
            "allow_multiple": True,
            "allowed_tool_names": ["knowledge.search", "risk.score_account"],
            "fallback_tool": "knowledge.search",
        },
        retrieval_context={"rag_enabled": False, "retrieved_chunks": []},
        guardrail_context={
            "input_checks": [],
            "output_constraints": [],
            "allowed_action_scope": "analysis_only",
            "escalation_required": False,
        },
    )

    assert "Available tools: knowledge.search, risk.score_account." in planner_prompt
    assert "Retrieval context status: empty;" in planner_prompt
    assert "Guardrail context:" in planner_prompt
