from collections.abc import Callable

from backend.mcp_gateway.models import MCPToolDefinition, ToolInvocationResult
from backend.services.common import extract_query_text
from backend.services.knowledge import KnowledgeService
from backend.services.operations import OperationsService
from backend.services.risk import RiskService
from backend.services.trade import TradeService

ToolInvocationHandler = Callable[
    [MCPToolDefinition, dict[str, object]],
    ToolInvocationResult,
]


def _build_completed_result(
    tool_definition: MCPToolDefinition,
    request_payload: dict[str, object],
    response_payload: dict[str, object],
) -> ToolInvocationResult:
    return ToolInvocationResult(
        tool_name=tool_definition.name,
        domain=tool_definition.domain,
        invocation_status="completed",
        request_payload=request_payload,
        response_payload=response_payload,
    )


def build_default_tool_handlers(
    knowledge_service: KnowledgeService,
    risk_service: RiskService,
    trade_service: TradeService,
    operations_service: OperationsService,
) -> dict[str, ToolInvocationHandler]:
    def handle_knowledge_search(
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        query_text = extract_query_text(request_payload)
        response_payload = knowledge_service.search(query_text=query_text, limit=3)
        return _build_completed_result(tool_definition, request_payload, response_payload)

    def handle_risk_score_account(
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        query_text = extract_query_text(request_payload)
        response_payload = risk_service.score_account(query_text=query_text, limit=3)
        return _build_completed_result(tool_definition, request_payload, response_payload)

    def handle_trade_query_metrics(
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        query_text = extract_query_text(request_payload)
        response_payload = trade_service.query_metrics(query_text=query_text, limit=3)
        return _build_completed_result(tool_definition, request_payload, response_payload)

    def handle_ops_create_alert_or_action(
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        query_text = extract_query_text(request_payload)
        response_payload = operations_service.create_alert_or_action(
            query_text=query_text,
            limit=3,
        )
        return _build_completed_result(tool_definition, request_payload, response_payload)

    return {
        "knowledge.search": handle_knowledge_search,
        "risk.score_account": handle_risk_score_account,
        "trade.query_metrics": handle_trade_query_metrics,
        "ops.create_alert_or_action": handle_ops_create_alert_or_action,
    }
