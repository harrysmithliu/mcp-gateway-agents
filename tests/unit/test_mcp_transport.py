from backend.mcp_gateway.contracts import CORE_MCP_TOOL_NAMES
from backend.mcp_gateway.models import MCPToolDefinition, ToolInvocationResult
from backend.mcp_gateway.transport import MCPTransportRouter


class FakeRegistry:
    def __init__(self) -> None:
        self.registry_calls: list[str] = []

    def get_tool(self, tool_name: str) -> MCPToolDefinition | None:
        domains = {
            "knowledge.search": "knowledge",
            "risk.score_account": "risk",
            "trade.query_metrics": "trade",
            "ops.create_alert_or_action": "operations",
        }
        domain = domains.get(tool_name)
        if domain is None:
            return None
        return MCPToolDefinition(
            name=tool_name,
            domain=domain,
            description="Fake tool.",
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
        self.calls: list[tuple[str, dict[str, object], dict[str, object] | None]] = []

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, object],
        server_authorization_context: dict[str, object] | None = None,
    ):
        self.calls.append((tool_name, arguments, server_authorization_context))
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


def test_sdk_mode_routes_all_core_tools_through_the_sdk_client() -> None:
    registry = FakeRegistry()
    sdk_client = FakeSDKClient()
    router = MCPTransportRouter(
        registry=registry,
        transport_mode="sdk_stdio",
        sdk_client=sdk_client,
    )

    payloads = {
        "knowledge.search": {
            "query": "policy",
            "access_level": "restricted",
            "authorization_context": {
                "access_level": "internal",
                "allowed_access_levels": ["internal"],
            },
        },
        "risk.score_account": {"query": "account", "limit": 2},
        "trade.query_metrics": {"query": "atlas trade", "limit": 2},
        "ops.create_alert_or_action": {"query": "alert review", "limit": 2},
    }

    results = {
        tool_name: router.invoke(tool_name, request_payload)
        for tool_name, request_payload in payloads.items()
    }

    assert all(result.response_payload == {"source": "sdk"} for result in results.values())
    assert all(result.transport == "sdk_stdio" for result in results.values())
    assert sdk_client.calls == [
        (
            "knowledge.search",
            {"query": "policy"},
            {
                "access_level": "internal",
                "allowed_access_levels": ["internal"],
            },
        ),
        ("risk.score_account", {"query": "account", "limit": 2}, None),
        ("trade.query_metrics", {"query": "atlas trade", "limit": 2}, None),
        (
            "ops.create_alert_or_action",
            {"query": "alert review", "limit": 2},
            None,
        ),
    ]
    assert registry.registry_calls == []


def test_sdk_failure_falls_back_to_registry() -> None:
    registry = FakeRegistry()

    class FailingSDKClient:
        async def call_tool(
            self,
            tool_name: str,
            arguments: dict[str, object],
            server_authorization_context: dict[str, object] | None = None,
        ):
            raise RuntimeError("transport unavailable")

    router = MCPTransportRouter(
        registry=registry,
        transport_mode="sdk_stdio",
        sdk_client=FailingSDKClient(),
    )

    result = router.invoke("knowledge.search", {"query": "policy"})

    assert result.response_payload == {"source": "registry"}
    assert registry.registry_calls == ["knowledge.search"]


def test_sdk_knowledge_disabled_payload_maps_to_unavailable_invocation() -> None:
    registry = FakeRegistry()

    class DisabledSDKClient:
        async def call_tool(
            self,
            tool_name: str,
            arguments: dict[str, object],
            server_authorization_context: dict[str, object] | None = None,
        ):
            return type(
                "FakeClientResult",
                (),
                {
                    "structured_content": {
                        "result_status": "disabled",
                        "citations": [],
                    },
                    "is_error": False,
                },
            )()

    router = MCPTransportRouter(
        registry=registry,
        transport_mode="sdk_stdio",
        sdk_client=DisabledSDKClient(),
    )

    result = router.invoke("knowledge.search", {"query": "policy"})

    assert result.invocation_status == "unavailable"
    assert result.response_payload["result_status"] == "disabled"
