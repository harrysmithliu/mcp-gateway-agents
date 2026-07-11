from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass(frozen=True, slots=True)
class MCPClientToolResult:
    """Safe project-facing result from one MCP client session call."""

    tool_name: str
    available_tool_names: list[str]
    structured_content: dict[str, object]
    is_error: bool = False


@dataclass(slots=True)
class MCPStdioClient:
    """Runs one MCP server subprocess for an isolated SDK session."""

    server_module: str = "backend.mcp_gateway.server"
    command: str = sys.executable
    cwd: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])
    server_runtime: str = "preview"

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, object] | None = None,
    ) -> MCPClientToolResult:
        server_environment = os.environ.copy()
        server_environment["MCP_SERVER_RUNTIME"] = self.server_runtime
        server_parameters = StdioServerParameters(
            command=self.command,
            args=["-m", self.server_module],
            cwd=str(self.cwd),
            env=server_environment,
        )
        async with stdio_client(server_parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tool_list = await session.list_tools()
                call_result = await session.call_tool(
                    tool_name,
                    arguments=arguments or {},
                )

        structured_content = getattr(call_result, "structured_content", None)
        if not isinstance(structured_content, dict):
            structured_content = getattr(call_result, "structuredContent", {})
        return MCPClientToolResult(
            tool_name=tool_name,
            available_tool_names=[tool.name for tool in tool_list.tools],
            structured_content=(
                structured_content if isinstance(structured_content, dict) else {}
            ),
            is_error=bool(getattr(call_result, "isError", False)),
        )
