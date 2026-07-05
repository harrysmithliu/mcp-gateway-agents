from typing import Protocol

from backend.agent.models import ChatCommand, ChatResult, PlannerResult
from backend.guardrails.policy import GuardrailDecision
from backend.mcp_gateway.registry import MCPToolDefinition, ToolInvocationResult
from backend.retrieval.service import RetrievalContext


class ToolGatewayPort(Protocol):
    """Minimal registry-shaped port for planning and invocation."""

    def get_tool(self, tool_name: str) -> MCPToolDefinition | None: ...

    def list_tool_names(self) -> list[str]: ...

    def preview_knowledge_matches(
        self,
        query_text: str,
        limit: int = 3,
    ) -> list[dict[str, object]]: ...

    def invoke(
        self,
        tool_name: str,
        request_payload: dict[str, object] | None = None,
    ) -> ToolInvocationResult: ...


class PlannerPort(Protocol):
    """Top-level planner contract for selecting tools from a chat command."""

    def plan(
        self,
        command: ChatCommand,
        tool_gateway: ToolGatewayPort,
    ) -> PlannerResult: ...


class RetrieverPort(Protocol):
    """Future retrieval contract for assembling planner context."""

    def build_context(
        self,
        command: ChatCommand,
        tool_gateway: ToolGatewayPort,
    ) -> RetrievalContext: ...


class GuardrailPort(Protocol):
    """Future guardrail contract for pre-checks and planner context."""

    def build_context(
        self,
        command: ChatCommand,
    ) -> GuardrailDecision: ...

    def check_sensitive_action(
        self,
        command: ChatCommand,
    ) -> ChatResult | None: ...
