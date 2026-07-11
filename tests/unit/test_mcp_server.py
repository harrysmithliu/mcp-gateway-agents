import pytest

pytest.importorskip("mcp")

from backend.mcp_gateway.models import MCPToolDefinition, ToolInvocationResult
from backend.mcp_gateway.server import (
    KNOWLEDGE_SEARCH_TOOL_NAME,
    build_mcp_server,
)


class FakeRegistry:
    def __init__(self) -> None:
        self.invocations: list[tuple[str, dict[str, object] | None]] = []

    def get_tool(self, tool_name: str) -> MCPToolDefinition | None:
        return MCPToolDefinition(
            name=tool_name,
            domain="knowledge",
            description="Fake knowledge tool.",
        )

    def list_tool_names(self) -> list[str]:
        return [KNOWLEDGE_SEARCH_TOOL_NAME]

    def preview_knowledge_matches(
        self,
        query_text: str,
        limit: int = 3,
    ) -> list[dict[str, object]]:
        return []

    def invoke(
        self,
        tool_name: str,
        request_payload: dict[str, object] | None = None,
    ) -> ToolInvocationResult:
        self.invocations.append((tool_name, request_payload))
        return ToolInvocationResult(
            tool_name=tool_name,
            domain="knowledge",
            invocation_status="completed",
            request_payload=request_payload or {},
            response_payload={
                "citations": [{"document_id": "doc-1"}],
                "retrieval_metadata": {"status": "completed"},
            },
        )


def test_build_mcp_server_registers_knowledge_search() -> None:
    server = build_mcp_server(FakeRegistry())

    tools = server._tool_manager.list_tools()

    assert [tool.name for tool in tools] == [KNOWLEDGE_SEARCH_TOOL_NAME]
    assert tools[0].parameters["properties"]["query"]["type"] == "string"


def test_mcp_knowledge_search_reuses_registry_invocation() -> None:
    registry = FakeRegistry()
    server = build_mcp_server(registry)
    tool = server._tool_manager.get_tool(KNOWLEDGE_SEARCH_TOOL_NAME)

    assert tool is not None
    response_payload = tool.fn(
        query="policy evidence",
        top_k=2,
        jurisdiction="CA",
        tags=["policy"],
    )

    assert registry.invocations == [
        (
            KNOWLEDGE_SEARCH_TOOL_NAME,
            {
                "query": "policy evidence",
                "top_k": 2,
                "jurisdiction": "CA",
                "tags": ["policy"],
            },
        )
    ]
    assert response_payload["citations"] == [{"document_id": "doc-1"}]
