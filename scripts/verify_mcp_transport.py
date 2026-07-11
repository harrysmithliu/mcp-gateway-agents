from __future__ import annotations

import json
import os

from backend.mcp_gateway.registry import build_default_registry
from backend.mcp_gateway.transport import build_mcp_transport_router


def main() -> int:
    server_runtime = os.getenv("MCP_SERVER_RUNTIME", "preview")
    router = build_mcp_transport_router(
        registry=build_default_registry(),
        transport_mode="sdk_stdio",
        server_runtime=server_runtime,
    )
    result = router.invoke(
        tool_name="knowledge.search",
        request_payload={"query": "policy evidence", "top_k": 2},
    )
    if result.invocation_status != "completed":
        raise RuntimeError("MCP SDK transport verification returned a failed invocation.")

    print(
        json.dumps(
            {
                "transport_mode": "sdk_stdio",
                "server_runtime": server_runtime,
                "tool_name": result.tool_name,
                "invocation_status": result.invocation_status,
                "mcp_transport": result.response_payload.get("mcp_transport"),
                "total_matches": result.response_payload.get("total_matches", 0),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
