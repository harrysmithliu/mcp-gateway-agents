import asyncio

from backend.mcp_gateway.models import MCPToolDefinition, ToolInvocationResult
from backend.mcp_gateway.transport import MCPTransportRouter


class FakeRegistry:
    def __init__(self) -> None:
        self.registry_calls: list[str] = []

    def get_tool(self, tool_name: str) -> MCPToolDefinition | None:
        return MCPToolDefinition(
            name=tool_name,
            domain="knowledge",
            description="Fake tool.",
        )

    def list_tool_names(self) -> list[str]:
        return ["knowledge.search", "risk.score_account"]

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
        self.registry_calls.append(tool_name)
        return ToolInvocationResult(
            tool_name=tool_name,
            domain="knowledge",
            invocation_status="completed",
            request_payload=request_payload or {},
            response_payload={"source": "registry"},
        )


class FakeSDKClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, object],
    ):
        self.calls.append((tool_name, arguments))
        return type(
            "FakeClientResult",
            (),
            {
                "structured_content": {"source": "sdk"},
                "is_error": False,
            },
        )()


def test_registry_mode_keeps_registry_invocation_default() -> None:
    registry = FakeRegistry()
    sdk_client = FakeSDKClient()
    router = MCPTransportRouter(
        registry=registry,
        transport_mode="registry",
        sdk_client=sdk_client,
    )

    result = router.invoke("knowledge.search", {"query": "policy"})

    assert result.response_payload == {"source": "registry"}
    assert registry.registry_calls == ["knowledge.search"]
    assert sdk_client.calls == []


def test_sdk_mode_routes_allowlisted_tool_and_preserves_other_tools() -> None:
    registry = FakeRegistry()
    sdk_client = FakeSDKClient()
    router = MCPTransportRouter(
        registry=registry,
        transport_mode="sdk_stdio",
        sdk_client=sdk_client,
    )

    sdk_result = router.invoke("knowledge.search", {"query": "policy"})
    registry_result = router.invoke("risk.score_account", {"query": "account"})

    assert sdk_result.response_payload == {
        "source": "sdk",
        "mcp_transport": "sdk_stdio",
    }
    assert registry_result.response_payload == {"source": "registry"}
    assert sdk_client.calls == [("knowledge.search", {"query": "policy"})]
    assert registry.registry_calls == ["risk.score_account"]


def test_sdk_failure_falls_back_to_registry() -> None:
    registry = FakeRegistry()

    class FailingSDKClient:
        async def call_tool(self, tool_name: str, arguments: dict[str, object]):
            raise RuntimeError("transport unavailable")

    router = MCPTransportRouter(
        registry=registry,
        transport_mode="sdk_stdio",
        sdk_client=FailingSDKClient(),
    )

    result = router.invoke("knowledge.search", {"query": "policy"})

    assert result.response_payload == {"source": "registry"}
    assert registry.registry_calls == ["knowledge.search"]
