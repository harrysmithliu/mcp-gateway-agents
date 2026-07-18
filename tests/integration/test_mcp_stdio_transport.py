import asyncio

import pytest

pytest.importorskip("mcp")

from backend.mcp_gateway.client import MCPStdioClient


def test_mcp_stdio_client_initializes_lists_and_calls_each_core_tool() -> None:
    calls = (
        ("knowledge.search", {"query": "policy evidence", "top_k": 2}),
        ("risk.score_account", {"query": "atlas risk", "limit": 2}),
        ("trade.query_metrics", {"query": "atlas trade", "limit": 2}),
        ("ops.create_alert_or_action", {"query": "alert review", "limit": 2}),
    )

    results = [
        asyncio.run(MCPStdioClient().call_tool(tool_name=tool_name, arguments=arguments))
        for tool_name, arguments in calls
    ]

    expected_tool_names = [tool_name for tool_name, _ in calls]
    assert all(result.is_error is False for result in results)
    assert all(result.available_tool_names == expected_tool_names for result in results)
    assert [result.tool_name for result in results] == expected_tool_names
    assert results[0].structured_content["total_matches"] >= 0
    assert results[1].structured_content["profiles"]
    assert results[2].structured_content["snapshots"]
    assert results[3].structured_content["templates"]
