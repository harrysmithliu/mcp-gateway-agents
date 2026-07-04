from dataclasses import dataclass, field


@dataclass(slots=True)
class AgentResponse:
    """Structured placeholder response for the future chat workflow."""

    reply_text: str
    tool_names: list[str] = field(default_factory=list)
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
        evidence: list[str] = []
        actions: list[str] = []

        for rule in TOOL_ROUTING_RULES:
            if not any(keyword in lowered_text for keyword in rule.keywords):
                continue

            tool_names.append(rule.tool_name)

            if rule.evidence_note:
                evidence.append(rule.evidence_note)

            if rule.privileged_action and rule.fallback_action:
                actions.append(
                    rule.privileged_action
                    if normalized_role in ACTION_ENABLED_ROLES
                    else rule.fallback_action
                )

        if not tool_names:
            tool_names.append(DEFAULT_TOOL_NAME)
            evidence.append(DEFAULT_EVIDENCE_NOTE)

        return AgentResponse(
            reply_text=(
                f"Prepared a placeholder agent response for the {normalized_role or 'unknown'} "
                "role. The API layer can route this into LangChain and MCP execution next."
            ),
            tool_names=tool_names,
            evidence=evidence,
            actions=actions,
        )
