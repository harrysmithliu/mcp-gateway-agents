import pytest

pytest.importorskip("mcp")

from backend.mcp_gateway.registry import build_default_registry
from backend.mcp_gateway.transport import build_mcp_transport_router


def test_sdk_stdio_mode_preserves_each_core_registry_payload() -> None:
    registry = build_default_registry()
    router = build_mcp_transport_router(
        registry=registry,
        transport_mode="sdk_stdio",
        server_runtime="preview",
    )
    calls = (
        ("knowledge.search", {"query": "policy evidence", "top_k": 2}),
        ("risk.score_account", {"query": "atlas risk"}),
        ("trade.query_metrics", {"query": "atlas trade"}),
        ("ops.create_alert_or_action", {"query": "alert review"}),
    )

    for tool_name, request_payload in calls:
        expected_result = registry.invoke(tool_name, request_payload)
        sdk_result = router.invoke(tool_name, request_payload)

        assert sdk_result.invocation_status == expected_result.invocation_status
        assert sdk_result.transport == "sdk_stdio"
        assert sdk_result.response_payload == expected_result.response_payload
