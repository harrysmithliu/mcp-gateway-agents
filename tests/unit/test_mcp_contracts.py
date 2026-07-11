from backend.mcp_gateway.contracts import (
    build_mcp_tool_call,
    build_mcp_tool_descriptor,
    build_tool_invocation_result,
)
from backend.mcp_gateway.models import MCPToolDefinition


def test_build_mcp_tool_descriptor_preserves_registry_metadata() -> None:
    descriptor = build_mcp_tool_descriptor(
        MCPToolDefinition(
            name="knowledge.search",
            domain="knowledge",
            description="Search internal knowledge.",
        )
    )

    assert descriptor.name == "knowledge.search"
    assert descriptor.domain == "knowledge"
    assert descriptor.description == "Search internal knowledge."
    assert descriptor.input_schema == {
        "type": "object",
        "additionalProperties": True,
    }


def test_build_mcp_tool_call_copies_request_arguments() -> None:
    request_payload = {"query": "policy evidence", "top_k": 2}

    tool_call = build_mcp_tool_call("knowledge.search", request_payload)

    assert tool_call.tool_name == "knowledge.search"
    assert tool_call.arguments == request_payload
    assert tool_call.arguments is not request_payload


def test_build_tool_invocation_result_preserves_structured_payload() -> None:
    tool_call = build_mcp_tool_call("knowledge.search", {"query": "policy"})

    result = build_tool_invocation_result(
        tool_call=tool_call,
        domain="knowledge",
        invocation_status="completed",
        response_payload={
            "citations": [{"document_id": "doc-1"}],
            "retrieval_metadata": {"status": "completed"},
        },
    )

    assert result.tool_name == "knowledge.search"
    assert result.invocation_status == "completed"
    assert result.request_payload == {"query": "policy"}
    assert result.response_payload["citations"] == [{"document_id": "doc-1"}]
