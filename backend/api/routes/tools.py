from typing import Annotated

from fastapi import APIRouter, Depends

from backend.agent.ports import ToolGatewayPort
from backend.api.dependencies import get_tool_registry
from backend.api.mappers import build_tool_invocation_result_response
from backend.api.schemas.chat import ChatResponse
from backend.api.schemas.tools import (
    KnowledgeSearchRequest,
    OpsCreateAlertOrActionRequest,
    RiskScoreAccountRequest,
    TradeQueryMetricsRequest,
)

router = APIRouter(tags=["tools"])


def _invoke_tool(
    tool_name: str,
    query: str,
    registry: ToolGatewayPort,
    request_payload: dict[str, object] | None = None,
) -> ChatResponse.ToolInvocationResultResponse:
    payload = {"query": query.strip()}
    if request_payload:
        payload.update(request_payload)
    tool_invocation_result = registry.invoke(
        tool_name=tool_name,
        request_payload=payload,
    )
    return build_tool_invocation_result_response(tool_invocation_result)


@router.post(
    "/tools/knowledge-search",
    response_model=ChatResponse.ToolInvocationResultResponse,
)
def knowledge_search(
    request: KnowledgeSearchRequest,
    registry: Annotated[ToolGatewayPort, Depends(get_tool_registry)],
) -> ChatResponse.ToolInvocationResultResponse:
    return _invoke_tool(
        tool_name="knowledge.search",
        query=request.query,
        registry=registry,
        request_payload={
            "top_k": request.top_k,
            "access_level": request.access_level,
            "jurisdiction": request.jurisdiction,
            "tags": request.tags,
        },
    )


@router.post(
    "/tools/risk-score-account",
    response_model=ChatResponse.ToolInvocationResultResponse,
)
def risk_score_account(
    request: RiskScoreAccountRequest,
    registry: Annotated[ToolGatewayPort, Depends(get_tool_registry)],
) -> ChatResponse.ToolInvocationResultResponse:
    return _invoke_tool(
        tool_name="risk.score_account",
        query=request.query,
        registry=registry,
    )


@router.post(
    "/tools/trade-query-metrics",
    response_model=ChatResponse.ToolInvocationResultResponse,
)
def trade_query_metrics(
    request: TradeQueryMetricsRequest,
    registry: Annotated[ToolGatewayPort, Depends(get_tool_registry)],
) -> ChatResponse.ToolInvocationResultResponse:
    return _invoke_tool(
        tool_name="trade.query_metrics",
        query=request.query,
        registry=registry,
    )


@router.post(
    "/tools/ops-create-alert-or-action",
    response_model=ChatResponse.ToolInvocationResultResponse,
)
def ops_create_alert_or_action(
    request: OpsCreateAlertOrActionRequest,
    registry: Annotated[ToolGatewayPort, Depends(get_tool_registry)],
) -> ChatResponse.ToolInvocationResultResponse:
    return _invoke_tool(
        tool_name="ops.create_alert_or_action",
        query=request.query,
        registry=registry,
    )
