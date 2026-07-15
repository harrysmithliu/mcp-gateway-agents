import pytest

pytest.importorskip("mcp")

from backend.mcp_gateway.registry import build_default_registry
from backend.mcp_gateway.transport import build_mcp_transport_router


def test_sdk_stdio_mode_routes_knowledge_search_through_local_mcp() -> None:
    router = build_mcp_transport_router(
        registry=build_default_registry(),
        transport_mode="sdk_stdio",
        server_runtime="preview",
    )

    result = router.invoke(
        tool_name="knowledge.search",
        request_payload={"query": "policy evidence", "top_k": 2},
    )

    assert result.invocation_status == "completed"
    assert result.transport == "sdk_stdio"
    assert result.response_payload["contract_version"] == "knowledge.search/v1"
    assert "mcp_transport" not in result.response_payload
    assert result.response_payload["query"] == "policy evidence"
