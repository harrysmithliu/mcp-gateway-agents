from dataclasses import dataclass, field


@dataclass(slots=True)
class ToolRegistry:
    """Minimal registry placeholder for later MCP tool wiring."""

    tool_names: list[str] = field(default_factory=list)

    def register(self, tool_name: str) -> None:
        if tool_name not in self.tool_names:
            self.tool_names.append(tool_name)

