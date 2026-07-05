from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MCPToolDefinition:
    """Minimal MCP tool metadata for the current runnable loop."""

    name: str
    domain: str
    description: str


@dataclass(slots=True)
class ToolInvocationResult:
    """Result envelope for the registry-driven tool invocation seam."""

    tool_name: str
    domain: str
    invocation_status: str
    request_payload: dict[str, object] = field(default_factory=dict)
    response_payload: dict[str, object] = field(default_factory=dict)
