from collections.abc import Callable

from backend.mcp_gateway.models import MCPToolDefinition, ToolInvocationResult
from backend.retrieval.contracts import RetrievalQuery
from backend.retrieval.service import RetrievalService
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
    retrieval_service: RetrievalService | None = None,
) -> dict[str, ToolInvocationHandler]:
    def handle_knowledge_search(
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        query_text = extract_query_text(request_payload)
        if retrieval_service is not None:
            retrieval_query = _build_retrieval_query(
                query_text=query_text,
                request_payload=request_payload,
            )
            retrieval_result = retrieval_service.retrieve(retrieval_query)
            response_payload = retrieval_result.to_payload()
            response_payload["query"] = retrieval_query.text
            response_payload["total_matches"] = retrieval_result.metadata.result_count
            return ToolInvocationResult(
                tool_name=tool_definition.name,
                domain=tool_definition.domain,
                invocation_status=(
                    "failed"
                    if retrieval_result.metadata.status == "failed"
                    else "completed"
                ),
                request_payload=request_payload,
                response_payload=response_payload,
            )

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


def _build_retrieval_query(
    query_text: str,
    request_payload: dict[str, object],
) -> RetrievalQuery:
    raw_top_k = request_payload.get("top_k", 3)
    top_k = raw_top_k if isinstance(raw_top_k, int) and not isinstance(raw_top_k, bool) else 3
    if not 1 <= top_k <= 50:
        top_k = 3

    raw_tags = request_payload.get("tags", [])
    tags = (
        tuple(tag.strip() for tag in raw_tags if isinstance(tag, str) and tag.strip())
        if isinstance(raw_tags, (list, tuple))
        else ()
    )
    return RetrievalQuery(
        text=query_text,
        top_k=top_k,
        access_level=_build_authorized_access_level(request_payload),
        jurisdiction=_optional_string(request_payload.get("jurisdiction")),
        tags=tags,
    )


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _build_authorized_access_level(request_payload: dict[str, object]) -> str | None:
    authorization_context = request_payload.get("authorization_context")
    if isinstance(authorization_context, dict):
        return _optional_string(authorization_context.get("access_level"))
    return _optional_string(request_payload.get("access_level"))
