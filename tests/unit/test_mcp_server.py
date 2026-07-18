import pytest

pytest.importorskip("mcp")

from backend.mcp_gateway.contracts import (
    CORE_MCP_TOOL_NAMES,
    KNOWLEDGE_SEARCH_TOOL_NAME,
    OPS_CREATE_ALERT_OR_ACTION_TOOL_NAME,
    RISK_SCORE_ACCOUNT_TOOL_NAME,
    TRADE_QUERY_METRICS_TOOL_NAME,
)
from backend.mcp_gateway.models import MCPToolDefinition, ToolInvocationResult
from backend.mcp_gateway.server import (
    build_server_authorization_context,
    build_mcp_server,
)


class FakeRegistry:
    def __init__(self) -> None:
        self.invocations: list[tuple[str, dict[str, object] | None]] = []

    def get_tool(self, tool_name: str) -> MCPToolDefinition | None:
        definitions = {
            KNOWLEDGE_SEARCH_TOOL_NAME: ("knowledge", "Fake knowledge tool."),
            RISK_SCORE_ACCOUNT_TOOL_NAME: ("risk", "Fake risk tool."),
            TRADE_QUERY_METRICS_TOOL_NAME: ("trade", "Fake trade tool."),
            OPS_CREATE_ALERT_OR_ACTION_TOOL_NAME: ("operations", "Fake ops tool."),
        }
        definition = definitions.get(tool_name)
        if definition is None:
            return None
        return MCPToolDefinition(
            name=tool_name,
            domain=definition[0],
            description=definition[1],
        )

    def list_tool_names(self) -> list[str]:
        return list(CORE_MCP_TOOL_NAMES)

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
        if tool_name != KNOWLEDGE_SEARCH_TOOL_NAME:
            return ToolInvocationResult(
                tool_name=tool_name,
                domain=self.get_tool(tool_name).domain,
                invocation_status="completed",
                request_payload=request_payload or {},
                response_payload={
                    "tool_name": tool_name,
                    "query": (request_payload or {}).get("query"),
                    "limit": (request_payload or {}).get("limit"),
                },
            )
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


def test_build_mcp_server_registers_the_core_registry_tool_catalog() -> None:
    server = build_mcp_server(FakeRegistry())

    tools = server._tool_manager.list_tools()

    assert [tool.name for tool in tools] == list(CORE_MCP_TOOL_NAMES)
    assert tools[0].parameters["properties"]["query"]["type"] == "string"
    assert "access_level" not in tools[0].parameters["properties"]
    for tool in tools[1:]:
        properties = tool.parameters["properties"]
        assert properties["query"]["type"] == "string"
        assert properties["limit"]["type"] == "integer"
        assert properties["limit"]["default"] == 3


def test_server_authorization_context_defaults_to_internal(monkeypatch) -> None:
    monkeypatch.delenv("MCP_SERVER_ALLOWED_ACCESS_LEVELS", raising=False)

    assert build_server_authorization_context() == {
        "access_level": "internal",
        "allowed_access_levels": ["internal"],
    }


def test_server_authorization_context_accepts_trusted_hierarchical_scope(monkeypatch) -> None:
    monkeypatch.setenv(
        "MCP_SERVER_ALLOWED_ACCESS_LEVELS",
        '["internal", "restricted", "internal"]',
    )

    assert build_server_authorization_context() == {
        "access_level": "restricted",
        "allowed_access_levels": ["internal", "restricted"],
    }


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
                "authorization_context": {
                    "access_level": "internal",
                    "allowed_access_levels": ["internal"],
                },
                "jurisdiction": "CA",
                "tags": ["policy"],
            },
        )
    ]
    assert response_payload["citations"] == [{"document_id": "doc-1"}]


@pytest.mark.parametrize(
    ("tool_name", "query"),
    (
        (RISK_SCORE_ACCOUNT_TOOL_NAME, "atlas risk"),
        (TRADE_QUERY_METRICS_TOOL_NAME, "atlas trade"),
        (
            OPS_CREATE_ALERT_OR_ACTION_TOOL_NAME,
            "alert review",
        ),
    ),
)
def test_mcp_query_tool_adapters_reuse_registry_invocation(
    tool_name: str,
    query: str,
) -> None:
    registry = FakeRegistry()
    server = build_mcp_server(registry)
    tool = server._tool_manager.get_tool(tool_name)

    assert tool is not None
    response_payload = tool.fn(query=query, limit=2)

    assert registry.invocations == [
        (tool_name, {"query": query, "limit": 2}),
    ]
    assert response_payload == {
        "tool_name": tool_name,
        "query": query,
        "limit": 2,
    }
