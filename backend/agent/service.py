from dataclasses import dataclass, field

from backend.mcp_gateway.registry import ToolInvocationResult, build_default_registry


@dataclass(slots=True)
class PlannedToolCall:
    """Structured placeholder for the next tool invocation plan."""

    tool_name: str
    domain: str
    description: str


@dataclass(slots=True)
class AgentResponse:
    """Structured placeholder response for the future chat workflow."""

    reply_text: str
    tool_names: list[str] = field(default_factory=list)
    planned_tool_calls: list[PlannedToolCall] = field(default_factory=list)
    tool_invocation_results: list[ToolInvocationResult] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ToolRoutingRule:
    """Centralized placeholder rule for keyword-based tool routing."""

    tool_name: str
    keywords: tuple[str, ...]
    evidence_note: str | None = None
    privileged_action: str | None = None
    fallback_action: str | None = None


SENSITIVE_ACTION_KEYWORDS = ("freeze", "release", "unlock")
SENSITIVE_ACTION_ALLOWED_ROLES = frozenset({"supervisor", "admin"})
ACTION_ENABLED_ROLES = frozenset({"risk_operator", "supervisor", "admin"})

TOOL_ROUTING_RULES = (
    ToolRoutingRule(
        tool_name="knowledge.search",
        keywords=("policy", "playbook", "case", "knowledge"),
        evidence_note="RAG-backed citations will be attached after retrieval wiring is implemented.",
    ),
    ToolRoutingRule(
        tool_name="risk.score_account",
        keywords=("risk", "score", "borrower", "account"),
    ),
    ToolRoutingRule(
        tool_name="trade.query_metrics",
        keywords=("trade", "wallet", "order", "volume"),
    ),
    ToolRoutingRule(
        tool_name="ops.create_alert_or_action",
        keywords=("alert", "review", "escalate"),
        privileged_action="Prepare an alert or review action payload.",
        fallback_action="Draft an alert summary for a higher-privilege operator.",
    ),
)
DEFAULT_TOOL_NAME = "knowledge.search"
DEFAULT_EVIDENCE_NOTE = "Defaulting to knowledge retrieval until more tools are wired."


@dataclass(slots=True)
class AgentService:
    """Placeholder for future agent orchestration."""

    provider_name: str = "claude-compatible"

    def describe(self) -> str:
        return (
            "Placeholder agent service. "
            "Tool routing, cache, RAG, and guardrails will be added in later batches."
        )

    def handle_chat(self, user_role: str, message_text: str) -> AgentResponse:
        normalized_role = user_role.strip().lower()
        normalized_text = message_text.strip()
        lowered_text = normalized_text.lower()
        registry = build_default_registry()

        if not normalized_text:
            return AgentResponse(reply_text="Please provide a chat request.")

        if (
            any(keyword in lowered_text for keyword in SENSITIVE_ACTION_KEYWORDS)
            and normalized_role not in SENSITIVE_ACTION_ALLOWED_ROLES
        ):
            return AgentResponse(
                reply_text=(
                    "I can summarize the request, but I cannot recommend or initiate "
                    "that sensitive action for your current role."
                ),
                actions=["Escalate this request to a supervisor or admin."],
            )

        tool_names: list[str] = []
        planned_tool_calls: list[PlannedToolCall] = []
        tool_invocation_results: list[ToolInvocationResult] = []
        evidence: list[str] = []
        actions: list[str] = []

        for rule in TOOL_ROUTING_RULES:
            if not any(keyword in lowered_text for keyword in rule.keywords):
                continue

            tool_definition = registry.get_tool(rule.tool_name)
            if tool_definition is None:
                continue

            tool_names.append(rule.tool_name)
            planned_tool_calls.append(
                PlannedToolCall(
                    tool_name=tool_definition.name,
                    domain=tool_definition.domain,
                    description=tool_definition.description,
                )
            )

            if rule.evidence_note:
                evidence.append(rule.evidence_note)

            if rule.privileged_action and rule.fallback_action:
                actions.append(
                    rule.privileged_action
                    if normalized_role in ACTION_ENABLED_ROLES
                    else rule.fallback_action
                )

        if not tool_names:
            tool_definition = registry.get_tool(DEFAULT_TOOL_NAME)
            if tool_definition is not None:
                tool_names.append(DEFAULT_TOOL_NAME)
                planned_tool_calls.append(
                    PlannedToolCall(
                        tool_name=tool_definition.name,
                        domain=tool_definition.domain,
                        description=tool_definition.description,
                    )
                )
                evidence.append(DEFAULT_EVIDENCE_NOTE)

        if planned_tool_calls:
            request_payload = {
                "user_role": normalized_role or "unknown",
                "message_text": normalized_text,
            }
            for planned_tool_call in planned_tool_calls:
                tool_invocation_result = registry.invoke(
                    tool_name=planned_tool_call.tool_name,
                    request_payload=request_payload,
                )
                tool_invocation_results.append(tool_invocation_result)
                evidence.append(
                    "Tool invocation completed for "
                    f"{planned_tool_call.tool_name} "
                    f"with status {tool_invocation_result.invocation_status}."
                )

        return AgentResponse(
            reply_text=(
                f"Prepared a placeholder agent response for the {normalized_role or 'unknown'} "
                "role. The API layer can route this into LangChain and registry-backed MCP "
                "execution next."
            ),
            tool_names=tool_names,
            planned_tool_calls=planned_tool_calls,
            tool_invocation_results=tool_invocation_results,
            evidence=evidence,
            actions=actions,
        )
