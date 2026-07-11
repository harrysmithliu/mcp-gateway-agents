from backend.mcp_gateway.sdk_adapter import MCPSDKAdapter


def test_mcp_sdk_adapter_returns_stable_status_payload() -> None:
    adapter = MCPSDKAdapter()

    response_payload = adapter.build_sdk_status()

    assert "package_available" in response_payload
    assert response_payload["sdk_stable_line"] == "v1"
    assert response_payload["transport_mode"] == "registry"
    assert response_payload["server_runtime"] == "preview"
    assert response_payload["sdk_tool_names"] == ["knowledge.search"]
    assert "integration_mode" in response_payload
    assert "recommended_next_step" in response_payload
    assert isinstance(response_payload["client_symbols"], list)
    assert isinstance(response_payload["server_symbols"], list)


def test_mcp_sdk_adapter_preserves_configured_transport_mode() -> None:
    adapter = MCPSDKAdapter(transport_mode="sdk_stdio", server_runtime="runtime")

    response_payload = adapter.build_sdk_status()

    assert response_payload["transport_mode"] == "sdk_stdio"
    assert response_payload["server_runtime"] == "runtime"
