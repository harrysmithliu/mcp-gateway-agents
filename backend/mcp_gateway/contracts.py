from dataclasses import dataclass, field

from backend.mcp_gateway.models import MCPToolDefinition, ToolInvocationResult


KNOWLEDGE_SEARCH_TOOL_NAME = "knowledge.search"


@dataclass(frozen=True, slots=True)
class MCPToolDescriptor:
    """Transport-neutral description of a registry tool."""

    name: str
    domain: str
    description: str
    input_schema: dict[str, object] = field(
        default_factory=lambda: {
            "type": "object",
            "additionalProperties": True,
        }
    )


@dataclass(frozen=True, slots=True)
class MCPToolCall:
    """Normalized arguments for an MCP tool call."""

    tool_name: str
    arguments: dict[str, object] = field(default_factory=dict)


def build_mcp_tool_descriptor(
    tool_definition: MCPToolDefinition,
) -> MCPToolDescriptor:
    return MCPToolDescriptor(
        name=tool_definition.name,
        domain=tool_definition.domain,
        description=tool_definition.description,
    )


def build_mcp_tool_call(
    tool_name: str,
    request_payload: dict[str, object] | None = None,
) -> MCPToolCall:
    return MCPToolCall(
        tool_name=tool_name,
        arguments=dict(request_payload or {}),
    )


def build_mcp_client_arguments(
    request_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    """Keep server-owned authorization fields out of public MCP arguments."""

    arguments = dict(request_payload or {})
    arguments.pop("authorization_context", None)
    arguments.pop("access_level", None)
    return arguments


def build_tool_invocation_result(
    tool_call: MCPToolCall,
    domain: str,
    invocation_status: str,
    response_payload: dict[str, object] | None = None,
    transport: str = "registry",
) -> ToolInvocationResult:
    return ToolInvocationResult(
        tool_name=tool_call.tool_name,
        domain=domain,
        invocation_status=invocation_status,
        request_payload=dict(tool_call.arguments),
        response_payload=dict(response_payload or {}),
        transport=transport,
    )
