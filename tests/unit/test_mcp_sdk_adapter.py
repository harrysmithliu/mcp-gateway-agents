from backend.mcp_gateway.sdk_adapter import MCPSDKAdapter


def test_mcp_sdk_adapter_returns_stable_status_payload() -> None:
    adapter = MCPSDKAdapter()

    response_payload = adapter.build_sdk_status()

    assert "package_available" in response_payload
    assert "integration_mode" in response_payload
    assert "recommended_next_step" in response_payload
    assert isinstance(response_payload["client_symbols"], list)
    assert isinstance(response_payload["server_symbols"], list)
