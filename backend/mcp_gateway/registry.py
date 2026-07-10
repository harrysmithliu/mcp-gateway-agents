from collections.abc import Callable
from dataclasses import dataclass, field

from backend.mcp_gateway.models import MCPToolDefinition, ToolInvocationResult
from backend.mcp_gateway.tools.handlers import (
    ToolInvocationHandler,
    build_default_tool_handlers,
)
from backend.retrieval.service import RetrievalService
from backend.services.knowledge import KnowledgeService
from backend.services.operations import OperationsService
from backend.services.risk import RiskService
from backend.services.trade import TradeService
DEFAULT_MCP_TOOL_DEFINITIONS = (
    MCPToolDefinition(
        name="knowledge.search",
        domain="knowledge",
        description="Search internal knowledge and return evidence candidates.",
    ),
    MCPToolDefinition(
        name="risk.score_account",
        domain="risk",
        description="Score a single account for risk review.",
    ),
    MCPToolDefinition(
        name="trade.query_metrics",
        domain="trade",
        description="Retrieve trade and wallet metrics for analysis.",
    ),
    MCPToolDefinition(
        name="ops.create_alert_or_action",
        domain="operations",
        description="Prepare an alert or follow-up action payload.",
    ),
)


@dataclass(slots=True)
class ToolRegistry:
    """Minimal registry placeholder for later MCP tool wiring."""

    tools: dict[str, MCPToolDefinition] = field(default_factory=dict)
    handlers: dict[str, ToolInvocationHandler] = field(default_factory=dict)
    knowledge_preview_handler: Callable[[str, int], list[dict[str, object]]] | None = None

    def register(
        self,
        tool_definition: MCPToolDefinition,
        handler: ToolInvocationHandler | None = None,
    ) -> None:
        self.tools[tool_definition.name] = tool_definition
        if handler is not None:
            self.handlers[tool_definition.name] = handler

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self.tools

    def get_tool(self, tool_name: str) -> MCPToolDefinition | None:
        return self.tools.get(tool_name)

    def list_tool_names(self) -> list[str]:
        return list(self.tools)

    def invoke(
        self,
        tool_name: str,
        request_payload: dict[str, object] | None = None,
    ) -> ToolInvocationResult:
        tool_definition = self.get_tool(tool_name)
        if tool_definition is None:
            raise ValueError(f"Tool is not registered: {tool_name}")

        normalized_payload = request_payload or {}
        handler = self.handlers.get(tool_definition.name)
        if handler is not None:
            return handler(tool_definition, normalized_payload)

        return self._build_stub_result(tool_definition, normalized_payload)

    def _build_stub_result(
        self,
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        response_payload = {
            "message": f"Stub invocation completed for {tool_definition.name}.",
            "description": tool_definition.description,
        }

        return ToolInvocationResult(
            tool_name=tool_definition.name,
            domain=tool_definition.domain,
            invocation_status="stubbed",
            request_payload=request_payload,
            response_payload=response_payload,
        )

    def preview_knowledge_matches(
        self,
        query_text: str,
        limit: int = 3,
    ) -> list[dict[str, object]]:
        if self.knowledge_preview_handler is None:
            return []
        return self.knowledge_preview_handler(query_text, limit)


def build_default_registry(
    knowledge_service: KnowledgeService | None = None,
    risk_service: RiskService | None = None,
    trade_service: TradeService | None = None,
    operations_service: OperationsService | None = None,
    retrieval_service: RetrievalService | None = None,
) -> ToolRegistry:
    knowledge_service = knowledge_service or KnowledgeService()
    risk_service = risk_service or RiskService()
    trade_service = trade_service or TradeService()
    operations_service = operations_service or OperationsService()

    registry = ToolRegistry(
        knowledge_preview_handler=knowledge_service.preview_matches,
    )
    handlers = build_default_tool_handlers(
        knowledge_service=knowledge_service,
        risk_service=risk_service,
        trade_service=trade_service,
        operations_service=operations_service,
        retrieval_service=retrieval_service,
    )

    for tool_definition in DEFAULT_MCP_TOOL_DEFINITIONS:
        registry.register(
            tool_definition,
            handler=handlers.get(tool_definition.name),
        )
    return registry
