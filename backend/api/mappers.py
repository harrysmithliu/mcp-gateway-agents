from backend.agent.models import AgentResponse, ChatCommand, ChatHistoryMessage
from backend.auth.models import IdentityPrincipal
from backend.auth.context import AuthorizationContext
from backend.agent.ports import ToolGatewayPort
from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.mcp_gateway.models import ToolInvocationResult
from backend.mcp_gateway.registry import ToolRegistry


def build_chat_command(
    request: ChatRequest,
    principal: IdentityPrincipal | None = None,
) -> ChatCommand:
    return ChatCommand(
        user_role=principal.primary_role if principal is not None else request.user_role,
        message_text=request.message_text,
        session_id=request.session_id,
        user_id=principal.user_id if principal is not None else None,
        authorization_context=(
            AuthorizationContext.from_principal(principal).to_payload()
            if principal is not None
            else None
        ),
        recent_messages=[
            ChatHistoryMessage(
                role=recent_message.role,
                content=recent_message.content,
            )
            for recent_message in request.recent_messages
        ],
    )


def build_tool_invocation_result_response(
    tool_invocation_result: ToolInvocationResult,
) -> ChatResponse.ToolInvocationResultResponse:
    return ChatResponse.ToolInvocationResultResponse(
        tool_name=tool_invocation_result.tool_name,
        domain=tool_invocation_result.domain,
        invocation_status=tool_invocation_result.invocation_status,
        request_payload=tool_invocation_result.request_payload,
        response_payload=tool_invocation_result.response_payload,
    )


def build_chat_response(
    agent_response: AgentResponse,
    registry: ToolGatewayPort,
) -> ChatResponse:
    evidence = list(agent_response.evidence)
    matched_tool_notes: list[str] = []
    for tool_name in agent_response.tool_names:
        tool_definition = registry.get_tool(tool_name)
        if tool_definition is None:
            continue
        matched_tool_notes.append(
            f"Matched tool [{tool_definition.domain}]: "
            f"{tool_definition.name} - {tool_definition.description}"
        )

    evidence.extend(matched_tool_notes)
    evidence.append("Registered MCP tools: " + ", ".join(registry.list_tool_names()))

    return ChatResponse(
        session_id=agent_response.session_id,
        reply_text=agent_response.reply_text,
        tool_names=agent_response.tool_names,
        planned_tool_calls=[
            ChatResponse.PlannedToolCallResponse(
                tool_name=planned_tool_call.tool_name,
                domain=planned_tool_call.domain,
                description=planned_tool_call.description,
            )
            for planned_tool_call in agent_response.planned_tool_calls
        ],
        tool_invocation_results=[
            build_tool_invocation_result_response(tool_invocation_result)
            for tool_invocation_result in agent_response.tool_invocation_results
        ],
        evidence=evidence,
        actions=agent_response.actions,
        citations=[
            ChatResponse.CitationResponse(**citation)
            for citation in agent_response.citations
        ],
        cache_status=agent_response.cache_status,
        cache_reason=agent_response.cache_reason,
        planner_result=(
            ChatResponse.PlannerResultResponse(
                planner_source=agent_response.planner_result.planner_source,
                planner_mode=agent_response.planner_result.planner_mode,
                model_provider=agent_response.planner_result.model_provider,
                model_name=agent_response.planner_result.model_name,
                latency_ms=agent_response.planner_result.latency_ms,
                raw_output_text=agent_response.planner_result.raw_output_text,
                candidate_tool_names=agent_response.planner_result.candidate_tool_names,
                selected_tool_names=agent_response.planner_result.selected_tool_names,
                used_fallback=agent_response.planner_result.used_fallback,
                fallback_reason=agent_response.planner_result.fallback_reason,
                retrieval_status=agent_response.planner_result.retrieval_status,
                retrieval_source=agent_response.planner_result.retrieval_source,
                retrieval_result_count=agent_response.planner_result.retrieval_result_count,
                grounded_chunk_count=agent_response.planner_result.grounded_chunk_count,
                grounding_truncated=agent_response.planner_result.grounding_truncated,
            )
            if agent_response.planner_result is not None
            else None
        ),
    )
