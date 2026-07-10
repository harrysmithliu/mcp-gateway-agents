from backend.agent.service import AgentService
from backend.mcp_gateway.models import ToolInvocationResult


def test_agent_response_extracts_and_deduplicates_knowledge_citations() -> None:
    citation = {
        "document_id": "doc-1",
        "title": "Trading Policy",
        "chunk_id": "chunk-1",
        "chunk_index": 2,
        "source_path": "data/trading.md",
        "score": 0.91,
        "excerpt": "Escalate suspicious activity.",
    }
    tool_result = ToolInvocationResult(
        tool_name="knowledge.search",
        domain="knowledge",
        invocation_status="completed",
        response_payload={"citations": [citation, citation]},
    )

    response = AgentService().build_agent_response(
        normalized_role="analyst",
        session_id="session-citations",
        tool_names=["knowledge.search"],
        planned_tool_calls=[],
        tool_invocation_results=[tool_result],
        evidence=["knowledge search completed"],
        actions=[],
    )

    assert response.citations == [citation]
    assert response.evidence[-1] == "Evidence grounded by 1 knowledge citation(s)."
