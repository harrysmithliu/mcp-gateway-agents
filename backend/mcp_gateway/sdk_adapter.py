from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MCPSDKAdapter:
    transport_mode: str = "registry"
    server_runtime: str = "preview"

    def _import_mcp(self) -> Any:
        try:
            import mcp
        except ImportError:
            return None
        return mcp

    def build_sdk_status(self) -> dict[str, object]:
        mcp_module = self._import_mcp()
        if mcp_module is None:
            return {
                "package_available": False,
                "sdk_version": None,
                "sdk_stable_line": "v1",
                "transport_mode": self.transport_mode,
                "server_runtime": self.server_runtime,
                "sdk_tool_names": ["knowledge.search"],
                "integration_mode": "registry_fallback",
                "client_symbols": [],
                "server_symbols": [],
                "recommended_next_step": (
                    "Install the official modelcontextprotocol/python-sdk package "
                    "before switching runtime tool transport from the local registry."
                ),
            }

        client_symbols = sorted(
            symbol
            for symbol in dir(mcp_module)
            if "client" in symbol.lower() or symbol == "Client"
        )
        server_symbols = sorted(
            symbol
            for symbol in dir(mcp_module)
            if "server" in symbol.lower() or symbol == "MCPServer"
        )
        return {
            "package_available": True,
            "sdk_version": getattr(mcp_module, "__version__", "unknown"),
            "sdk_stable_line": "v1",
            "transport_mode": self.transport_mode,
            "server_runtime": self.server_runtime,
            "sdk_tool_names": ["knowledge.search"],
            "integration_mode": "sdk_ready",
            "client_symbols": client_symbols,
            "server_symbols": server_symbols,
            "recommended_next_step": (
                "Keep registry transport as the default and introduce the official "
                "MCP client/session lifecycle behind a switchable transport boundary."
            ),
        }
