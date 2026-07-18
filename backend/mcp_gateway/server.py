import json
import os
from mcp.server.fastmcp import FastMCP

from backend.agent.ports import ToolGatewayPort
from backend.mcp_gateway.contracts import (
    KNOWLEDGE_SEARCH_TOOL_NAME,
    OPS_CREATE_ALERT_OR_ACTION_TOOL_NAME,
    RISK_SCORE_ACCOUNT_TOOL_NAME,
    TRADE_QUERY_METRICS_TOOL_NAME,
)
from backend.mcp_gateway.registry import build_default_registry


MCP_SERVER_NAME = "Trading and Risk MCP Gateway"
def build_server_authorization_context() -> dict[str, object]:
    """Read the server-owned MCP scope injected by the trusted SDK launcher."""

    raw_levels = os.getenv("MCP_SERVER_ALLOWED_ACCESS_LEVELS", "").strip()
    levels: list[str] = []
    if raw_levels:
        try:
            parsed_levels = json.loads(raw_levels)
        except json.JSONDecodeError:
            parsed_levels = []
        if isinstance(parsed_levels, list):
            levels = list(
                dict.fromkeys(
                    level.strip()
                    for level in parsed_levels
                    if isinstance(level, str) and level.strip()
                )
            )
    if not levels:
        levels = ["internal"]
    return {
        "access_level": levels[-1],
        "allowed_access_levels": levels,
    }


def invoke_knowledge_search(
    registry: ToolGatewayPort,
    query: str,
    top_k: int = 3,
    jurisdiction: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, object]:
    request_payload: dict[str, object] = {
        "query": query,
        "top_k": top_k,
        "authorization_context": build_server_authorization_context(),
    }
    if jurisdiction is not None:
        request_payload["jurisdiction"] = jurisdiction
    if tags:
        request_payload["tags"] = tags

    invocation_result = registry.invoke(
        tool_name=KNOWLEDGE_SEARCH_TOOL_NAME,
        request_payload=request_payload,
    )
    return invocation_result.response_payload


def invoke_query_tool(
    registry: ToolGatewayPort,
    tool_name: str,
    query: str,
    limit: int = 3,
) -> dict[str, object]:
    """Invoke an existing read-only registry handler through the SDK boundary."""

    invocation_result = registry.invoke(
        tool_name=tool_name,
        request_payload={"query": query, "limit": limit},
    )
    return invocation_result.response_payload


def get_tool_description(registry: ToolGatewayPort, tool_name: str) -> str:
    tool_definition = registry.get_tool(tool_name)
    if tool_definition is None:
        raise ValueError(f"Tool is not registered: {tool_name}")
    return tool_definition.description


def build_mcp_server(registry: ToolGatewayPort | None = None) -> FastMCP:
    active_registry = registry or build_default_registry()
    server = FastMCP(MCP_SERVER_NAME)

    @server.tool(
        name=KNOWLEDGE_SEARCH_TOOL_NAME,
        description=get_tool_description(active_registry, KNOWLEDGE_SEARCH_TOOL_NAME),
        structured_output=True,
    )
    def knowledge_search(
        query: str,
        top_k: int = 3,
        jurisdiction: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        return invoke_knowledge_search(
            registry=active_registry,
            query=query,
            top_k=top_k,
            jurisdiction=jurisdiction,
            tags=tags,
        )

    @server.tool(
        name=RISK_SCORE_ACCOUNT_TOOL_NAME,
        description=get_tool_description(active_registry, RISK_SCORE_ACCOUNT_TOOL_NAME),
        structured_output=True,
    )
    def risk_score_account(query: str, limit: int = 3) -> dict[str, object]:
        return invoke_query_tool(
            registry=active_registry,
            tool_name=RISK_SCORE_ACCOUNT_TOOL_NAME,
            query=query,
            limit=limit,
        )

    @server.tool(
        name=TRADE_QUERY_METRICS_TOOL_NAME,
        description=get_tool_description(active_registry, TRADE_QUERY_METRICS_TOOL_NAME),
        structured_output=True,
    )
    def trade_query_metrics(query: str, limit: int = 3) -> dict[str, object]:
        return invoke_query_tool(
            registry=active_registry,
            tool_name=TRADE_QUERY_METRICS_TOOL_NAME,
            query=query,
            limit=limit,
        )

    @server.tool(
        name=OPS_CREATE_ALERT_OR_ACTION_TOOL_NAME,
        description=get_tool_description(
            active_registry,
            OPS_CREATE_ALERT_OR_ACTION_TOOL_NAME,
        ),
        structured_output=True,
    )
    def ops_create_alert_or_action(query: str, limit: int = 3) -> dict[str, object]:
        return invoke_query_tool(
            registry=active_registry,
            tool_name=OPS_CREATE_ALERT_OR_ACTION_TOOL_NAME,
            query=query,
            limit=limit,
        )

    return server


def build_stdio_registry() -> ToolGatewayPort:
    if os.getenv("MCP_SERVER_RUNTIME", "preview").strip().lower() != "runtime":
        return build_default_registry()

    from backend.retrieval.runtime import build_retrieval_service
    from backend.storage.runtime import build_storage_bundle
    from backend.storage.settings import get_settings

    settings = get_settings()
    storage_bundle = build_storage_bundle(settings)
    retrieval_service = build_retrieval_service(
        settings=settings,
        knowledge_search_repository=storage_bundle.knowledge_search_repository,
    )
    return build_default_registry(retrieval_service=retrieval_service)


def run_stdio_server() -> None:
    build_mcp_server(build_stdio_registry()).run(transport="stdio")


if __name__ == "__main__":
    run_stdio_server()
