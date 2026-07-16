from backend.agent.models import AgentResponse, PlannedToolCall, PlannerResult
from backend.cache.contracts import CacheStatus
from backend.mcp_gateway.models import ToolInvocationResult


def serialize_agent_response(response: AgentResponse) -> dict[str, object]:
    """Convert the structured response into a JSON-safe cache payload."""

    return {
        "reply_text": response.reply_text,
        "session_id": response.session_id,
        "tool_names": list(response.tool_names),
        "planned_tool_calls": [
            {
                "tool_name": item.tool_name,
                "domain": item.domain,
                "description": item.description,
            }
            for item in response.planned_tool_calls
        ],
        "tool_invocation_results": [
            {
                "tool_name": item.tool_name,
                "domain": item.domain,
                "invocation_status": item.invocation_status,
                "request_payload": dict(item.request_payload),
                "response_payload": dict(item.response_payload),
                "transport": item.transport,
            }
            for item in response.tool_invocation_results
        ],
        "evidence": list(response.evidence),
        "actions": list(response.actions),
        "planner_result": (
            {
                "planner_source": response.planner_result.planner_source,
                "raw_output_text": response.planner_result.raw_output_text,
                "candidate_tool_names": list(
                    response.planner_result.candidate_tool_names
                ),
                "selected_tool_names": list(response.planner_result.selected_tool_names),
                "used_fallback": response.planner_result.used_fallback,
                "fallback_reason": response.planner_result.fallback_reason,
                "planner_mode": response.planner_result.planner_mode,
                "model_provider": response.planner_result.model_provider,
                "model_name": response.planner_result.model_name,
                "latency_ms": response.planner_result.latency_ms,
                "retrieval_status": response.planner_result.retrieval_status,
                "retrieval_source": response.planner_result.retrieval_source,
                "retrieval_result_count": response.planner_result.retrieval_result_count,
                "grounded_chunk_count": response.planner_result.grounded_chunk_count,
                "grounding_truncated": response.planner_result.grounding_truncated,
                "history_source": response.planner_result.history_source,
                "history_fallback_reason": response.planner_result.history_fallback_reason,
            }
            if response.planner_result is not None
            else None
        ),
        "citations": [dict(citation) for citation in response.citations],
        "cache_status": response.cache_status,
        "cache_reason": response.cache_reason,
    }


def deserialize_agent_response(payload: dict[str, object]) -> AgentResponse:
    """Restore an AgentResponse and reject malformed cache envelopes."""

    planner_payload = payload.get("planner_result")
    planner_result = None
    if isinstance(planner_payload, dict):
        planner_result = PlannerResult(
            planner_source=str(planner_payload["planner_source"]),
            raw_output_text=planner_payload.get("raw_output_text"),
            candidate_tool_names=list(planner_payload.get("candidate_tool_names", [])),
            selected_tool_names=list(planner_payload.get("selected_tool_names", [])),
            used_fallback=bool(planner_payload.get("used_fallback", False)),
            fallback_reason=planner_payload.get("fallback_reason"),
            planner_mode=str(planner_payload.get("planner_mode", "legacy_text")),
            model_provider=planner_payload.get("model_provider"),
            model_name=planner_payload.get("model_name"),
            latency_ms=int(planner_payload.get("latency_ms", 0) or 0),
            retrieval_status=planner_payload.get("retrieval_status"),
            retrieval_source=planner_payload.get("retrieval_source"),
            retrieval_result_count=int(
                planner_payload.get("retrieval_result_count", 0) or 0
            ),
            grounded_chunk_count=int(
                planner_payload.get("grounded_chunk_count", 0) or 0
            ),
            grounding_truncated=bool(planner_payload.get("grounding_truncated", False)),
            history_source=str(
                planner_payload.get("history_source", "current_turn_only")
            ),
            history_fallback_reason=planner_payload.get("history_fallback_reason"),
        )

    return AgentResponse(
        reply_text=str(payload["reply_text"]),
        session_id=payload.get("session_id"),
        tool_names=list(payload.get("tool_names", [])),
        planned_tool_calls=[
            PlannedToolCall(
                tool_name=str(item["tool_name"]),
                domain=str(item["domain"]),
                description=str(item["description"]),
            )
            for item in payload.get("planned_tool_calls", [])
            if isinstance(item, dict)
        ],
        tool_invocation_results=[
            ToolInvocationResult(
                tool_name=str(item["tool_name"]),
                domain=str(item["domain"]),
                invocation_status=str(item["invocation_status"]),
                request_payload=dict(item.get("request_payload", {})),
                response_payload=dict(item.get("response_payload", {})),
                transport=str(item.get("transport", "registry")),
            )
            for item in payload.get("tool_invocation_results", [])
            if isinstance(item, dict)
        ],
        evidence=list(payload.get("evidence", [])),
        actions=list(payload.get("actions", [])),
        planner_result=planner_result,
        citations=[
            dict(citation)
            for citation in payload.get("citations", [])
            if isinstance(citation, dict)
        ],
        cache_status=str(payload.get("cache_status", CacheStatus.MISS.value)),
        cache_reason=payload.get("cache_reason"),
    )
