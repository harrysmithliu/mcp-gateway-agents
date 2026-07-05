from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.agent.service import AgentService
from backend.mcp_gateway.registry import build_default_registry

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    user_role: str = Field(..., min_length=1)
    message_text: str = Field(..., min_length=1)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)


class RiskScoreAccountRequest(BaseModel):
    query: str = Field(..., min_length=1)


class TradeQueryMetricsRequest(BaseModel):
    query: str = Field(..., min_length=1)


class OpsCreateAlertOrActionRequest(BaseModel):
    query: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    class PlannedToolCallResponse(BaseModel):
        tool_name: str
        domain: str
        description: str

    class ToolInvocationResultResponse(BaseModel):
        tool_name: str
        domain: str
        invocation_status: str
        request_payload: dict[str, object]
        response_payload: dict[str, object]

    reply_text: str
    tool_names: list[str]
    planned_tool_calls: list[PlannedToolCallResponse]
    tool_invocation_results: list[ToolInvocationResultResponse]
    evidence: list[str]
    actions: list[str]


def _build_tool_invocation_result_response(
    tool_name: str,
    query: str,
) -> ChatResponse.ToolInvocationResultResponse:
    registry = build_default_registry()
    tool_invocation_result = registry.invoke(
        tool_name=tool_name,
        request_payload={"query": query.strip()},
    )
    return ChatResponse.ToolInvocationResultResponse(
        tool_name=tool_invocation_result.tool_name,
        domain=tool_invocation_result.domain,
        invocation_status=tool_invocation_result.invocation_status,
        request_payload=tool_invocation_result.request_payload,
        response_payload=tool_invocation_result.response_payload,
    )


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    agent_service = AgentService()
    registry = build_default_registry()
    agent_response = agent_service.handle_chat(
        user_role=request.user_role,
        message_text=request.message_text,
    )
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
    evidence.append(
        "Registered MCP tools: " + ", ".join(registry.list_tool_names())
    )
    return ChatResponse(
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
            ChatResponse.ToolInvocationResultResponse(
                tool_name=tool_invocation_result.tool_name,
                domain=tool_invocation_result.domain,
                invocation_status=tool_invocation_result.invocation_status,
                request_payload=tool_invocation_result.request_payload,
                response_payload=tool_invocation_result.response_payload,
            )
            for tool_invocation_result in agent_response.tool_invocation_results
        ],
        evidence=evidence,
        actions=agent_response.actions,
    )


@router.post(
    "/tools/knowledge-search",
    response_model=ChatResponse.ToolInvocationResultResponse,
)
def knowledge_search(
    request: KnowledgeSearchRequest,
) -> ChatResponse.ToolInvocationResultResponse:
    return _build_tool_invocation_result_response(
        tool_name="knowledge.search",
        query=request.query,
    )


@router.post(
    "/tools/risk-score-account",
    response_model=ChatResponse.ToolInvocationResultResponse,
)
def risk_score_account(
    request: RiskScoreAccountRequest,
) -> ChatResponse.ToolInvocationResultResponse:
    return _build_tool_invocation_result_response(
        tool_name="risk.score_account",
        query=request.query,
    )


@router.post(
    "/tools/trade-query-metrics",
    response_model=ChatResponse.ToolInvocationResultResponse,
)
def trade_query_metrics(
    request: TradeQueryMetricsRequest,
) -> ChatResponse.ToolInvocationResultResponse:
    return _build_tool_invocation_result_response(
        tool_name="trade.query_metrics",
        query=request.query,
    )


@router.post(
    "/tools/ops-create-alert-or-action",
    response_model=ChatResponse.ToolInvocationResultResponse,
)
def ops_create_alert_or_action(
    request: OpsCreateAlertOrActionRequest,
) -> ChatResponse.ToolInvocationResultResponse:
    return _build_tool_invocation_result_response(
        tool_name="ops.create_alert_or_action",
        query=request.query,
    )
