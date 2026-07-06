from dataclasses import dataclass, field

from backend.mcp_gateway.registry import ToolInvocationResult


@dataclass(slots=True)
class PlannedToolCall:
    """Structured placeholder for the next tool invocation plan."""

    tool_name: str
    domain: str
    description: str


@dataclass(slots=True)
class ChatHistoryMessage:
    """Minimal request-supplied chat history message for planner context."""

    role: str
    content: str


@dataclass(slots=True)
class ChatCommand:
    """Top-level chat request contract for agent orchestration."""

    user_role: str
    message_text: str
    session_id: str | None = None
    recent_messages: list[ChatHistoryMessage] = field(default_factory=list)


@dataclass(slots=True)
class PlannerResult:
    """Structured planner trace for the current LangChain selection path."""

    planner_source: str
    raw_output_text: str | None = None
    candidate_tool_names: list[str] = field(default_factory=list)
    selected_tool_names: list[str] = field(default_factory=list)
    used_fallback: bool = False
    fallback_reason: str | None = None


@dataclass(slots=True)
class ChatResult:
    """Structured placeholder response for the future chat workflow."""

    reply_text: str
    session_id: str | None = None
    tool_names: list[str] = field(default_factory=list)
    planned_tool_calls: list[PlannedToolCall] = field(default_factory=list)
    tool_invocation_results: list[ToolInvocationResult] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    planner_result: PlannerResult | None = None


AgentResponse = ChatResult
