import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def isolate_default_http_knowledge_handler():
    """Keep HTTP smoke tests independent from the local model and PostgreSQL."""

    from backend.api.app import app
    from backend.mcp_gateway.models import ToolInvocationResult

    registry = app.state.container.tool_registry
    original_handler = registry.handlers.get("knowledge.search")
    agent_service = app.state.container.agent_service
    original_retrieval_service = agent_service.retrieval_service

    class PreviewOnlyRetrievalService:
        def build_context(self, normalized_text, tool_gateway, limit=2):
            return original_retrieval_service.build_context(
                normalized_text=normalized_text,
                tool_gateway=tool_gateway,
                limit=limit,
            )

    def test_handler(tool_definition, request_payload):
        return ToolInvocationResult(
            tool_name=tool_definition.name,
            domain=tool_definition.domain,
            invocation_status="completed",
            request_payload=request_payload,
            response_payload={
                "query": request_payload.get("query", ""),
                "total_matches": 0,
                "retrieval_source": "test_http_boundary",
                "retrieved_chunks": [],
                "citations": [],
            },
        )

    registry.handlers["knowledge.search"] = test_handler
    agent_service.retrieval_service = PreviewOnlyRetrievalService()
    try:
        yield
    finally:
        agent_service.retrieval_service = original_retrieval_service
        if original_handler is None:
            registry.handlers.pop("knowledge.search", None)
        else:
            registry.handlers["knowledge.search"] = original_handler
