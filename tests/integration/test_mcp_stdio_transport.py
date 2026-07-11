import asyncio

import pytest

pytest.importorskip("mcp")

from backend.mcp_gateway.client import MCPStdioClient


def test_mcp_stdio_client_initializes_lists_and_calls_tool() -> None:
    result = asyncio.run(
        MCPStdioClient().call_tool(
            tool_name="knowledge.search",
            arguments={"query": "policy evidence", "top_k": 2},
        )
    )

    assert result.is_error is False
    assert result.tool_name == "knowledge.search"
    assert result.available_tool_names == ["knowledge.search"]
    assert result.structured_content["query"] == "policy evidence"
    assert result.structured_content["total_matches"] >= 0
