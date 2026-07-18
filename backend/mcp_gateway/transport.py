from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from backend.agent.ports import ToolGatewayPort
from backend.mcp_gateway.contracts import (
    CORE_MCP_TOOL_NAMES,
    KNOWLEDGE_SEARCH_TOOL_NAME,
    build_mcp_client_arguments,
    build_mcp_tool_call,
    build_tool_invocation_result,
)
from backend.mcp_gateway.knowledge import build_knowledge_invocation_status


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MCPTransportRouter:
    """Switches selected tool calls between registry and MCP SDK transport."""

    registry: ToolGatewayPort
    transport_mode: str = "registry"
    sdk_client: Any | None = None
    server_runtime: str = "preview"
    sdk_tool_names: tuple[str, ...] = CORE_MCP_TOOL_NAMES

    def __getattr__(self, attribute_name: str) -> Any:
        """Keep registry-specific test and inspection access compatible."""

        return getattr(self.registry, attribute_name)

    def get_tool(self, tool_name: str):
        return self.registry.get_tool(tool_name)

    def list_tool_names(self) -> list[str]:
        return self.registry.list_tool_names()

    def preview_knowledge_matches(
        self,
        query_text: str,
        limit: int = 3,
    ) -> list[dict[str, object]]:
        return self.registry.preview_knowledge_matches(query_text, limit)

    def invoke(
        self,
        tool_name: str,
        request_payload: dict[str, object] | None = None,
    ):
        if (
            self.transport_mode != "sdk_stdio"
            or tool_name not in self.sdk_tool_names
            or self.sdk_client is None
        ):
            return self.registry.invoke(tool_name, request_payload)

        try:
            return self._invoke_with_sdk(tool_name, request_payload)
        except Exception as exc:
            logger.warning(
                "MCP SDK invocation fell back to registry",
                extra={
                    "tool_name": tool_name,
                    "transport_mode": self.transport_mode,
                    "error_type": type(exc).__name__,
                },
            )
            return self.registry.invoke(tool_name, request_payload)

    def _invoke_with_sdk(
        self,
        tool_name: str,
        request_payload: dict[str, object] | None,
    ):
        tool_definition = self.registry.get_tool(tool_name)
        if tool_definition is None:
            raise ValueError(f"Tool is not registered: {tool_name}")

        tool_call = build_mcp_tool_call(tool_name, request_payload)
        request_payload = request_payload or {}
        authorization_context = request_payload.get("authorization_context")
        authorization_context = (
            authorization_context if isinstance(authorization_context, dict) else None
        )
        client_result = asyncio.run(
            self.sdk_client.call_tool(
                tool_name=tool_name,
                arguments=build_mcp_client_arguments(request_payload),
                server_authorization_context=authorization_context,
            )
        )
        response_payload = dict(client_result.structured_content)
        invocation_status = "failed" if client_result.is_error else "completed"
        if tool_name == KNOWLEDGE_SEARCH_TOOL_NAME:
            invocation_status = build_knowledge_invocation_status(
                str(response_payload.get("result_status", "completed"))
            )
        return build_tool_invocation_result(
            tool_call=tool_call,
            domain=tool_definition.domain,
            invocation_status=invocation_status,
            response_payload=response_payload,
            transport="sdk_stdio",
        )


def build_mcp_transport_router(
    registry: ToolGatewayPort,
    transport_mode: str = "registry",
    server_runtime: str = "preview",
) -> MCPTransportRouter:
    normalized_mode = transport_mode.strip().lower() or "registry"
    sdk_client = None
    if normalized_mode == "sdk_stdio":
        from backend.mcp_gateway.client import MCPStdioClient

        sdk_client = MCPStdioClient(server_runtime=server_runtime)
    return MCPTransportRouter(
        registry=registry,
        transport_mode=normalized_mode,
        sdk_client=sdk_client,
        server_runtime=server_runtime,
    )
