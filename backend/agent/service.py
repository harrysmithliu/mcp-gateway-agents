from dataclasses import dataclass, field

from backend.mcp_gateway.registry import ToolInvocationResult, ToolRegistry, build_default_registry


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


@dataclass(frozen=True, slots=True)
class LangChainPlannerConfig:
    """Placeholder planner config before LangChain model wiring is enabled."""

    package_name: str
    model_provider: str
    model_name: str
    planner_mode: str


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
DEFAULT_LANGCHAIN_MODEL_PROVIDER = "anthropic"
DEFAULT_LANGCHAIN_MODEL_NAME = "claude-3-5-sonnet"
DEFAULT_LANGCHAIN_PLANNER_MODE = "tool-routing-placeholder"


@dataclass(slots=True)
class AgentService:
    """Placeholder for future agent orchestration."""

    provider_name: str = "claude-compatible"
    planner_override_output: str | None = None

    def describe(self) -> str:
        return (
            "Placeholder agent service. "
            "Tool routing, cache, RAG, and guardrails will be added in later batches."
        )

    def plan_tool_calls(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolRegistry,
    ) -> tuple[list[str], list[PlannedToolCall], list[str], list[str]]:
        lowered_text = normalized_text.lower()
        tool_names: list[str] = []
        planned_tool_calls: list[PlannedToolCall] = []
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

        return tool_names, planned_tool_calls, evidence, actions

    def build_langchain_planner_config(self) -> LangChainPlannerConfig:
        return LangChainPlannerConfig(
            package_name="langchain",
            model_provider=DEFAULT_LANGCHAIN_MODEL_PROVIDER,
            model_name=DEFAULT_LANGCHAIN_MODEL_NAME,
            planner_mode=DEFAULT_LANGCHAIN_PLANNER_MODE,
        )

    def build_langchain_tool_catalog(
        self,
        registry: ToolRegistry,
    ) -> list[dict[str, str]]:
        tool_catalog: list[dict[str, str]] = []
        for tool_name in registry.list_tool_names():
            tool_definition = registry.get_tool(tool_name)
            if tool_definition is None:
                continue

            tool_catalog.append(
                {
                    "tool_name": tool_definition.name,
                    "domain": tool_definition.domain,
                    "description": tool_definition.description,
                }
            )

        return tool_catalog

    def build_langchain_planner_prompt(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolRegistry,
    ) -> str:
        tool_catalog = self.build_langchain_tool_catalog(registry)
        available_tool_names = ", ".join(
            tool_entry["tool_name"] for tool_entry in tool_catalog
        )
        return (
            "You are the trading and risk operations planner. "
            "Select the best matching tools from the available tool list. "
            "Return only tool names as a comma-separated list. "
            f"User role: {normalized_role or 'unknown'}. "
            f"Available tools: {available_tool_names}. "
            f"User request: {normalized_text}"
        )

    def build_langchain_planner_payload(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolRegistry,
    ) -> dict[str, object]:
        planner_config = self.build_langchain_planner_config()
        tool_catalog = self.build_langchain_tool_catalog(registry)
        planner_prompt = self.build_langchain_planner_prompt(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
        )
        return {
            "planner_config": {
                "package_name": planner_config.package_name,
                "model_provider": planner_config.model_provider,
                "model_name": planner_config.model_name,
                "planner_mode": planner_config.planner_mode,
            },
            "user_role": normalized_role or "unknown",
            "message_text": normalized_text,
            "tool_catalog": tool_catalog,
            "planner_prompt": planner_prompt,
        }

    def init_langchain_chat_model(self) -> object | None:
        try:
            from langchain.chat_models import init_chat_model
        except ImportError:
            return None

        try:
            return init_chat_model(
                DEFAULT_LANGCHAIN_MODEL_NAME,
                model_provider=DEFAULT_LANGCHAIN_MODEL_PROVIDER,
            )
        except Exception:
            return None

    def extract_tool_names_from_langchain_output(
        self,
        planner_output_text: str,
        registry: ToolRegistry,
    ) -> list[str]:
        lowered_output = planner_output_text.lower()
        selected_tool_names: list[str] = []
        for tool_name in registry.list_tool_names():
            if tool_name.lower() not in lowered_output:
                continue
            selected_tool_names.append(tool_name)

        return selected_tool_names

    def build_tool_plan_from_names(
        self,
        selected_tool_names: list[str],
        normalized_role: str,
        registry: ToolRegistry,
    ) -> tuple[list[str], list[PlannedToolCall], list[str], list[str]]:
        tool_names: list[str] = []
        planned_tool_calls: list[PlannedToolCall] = []
        evidence: list[str] = []
        actions: list[str] = []
        routing_rules_by_tool_name = {
            routing_rule.tool_name: routing_rule for routing_rule in TOOL_ROUTING_RULES
        }

        for tool_name in selected_tool_names:
            tool_definition = registry.get_tool(tool_name)
            if tool_definition is None:
                continue

            tool_names.append(tool_definition.name)
            planned_tool_calls.append(
                PlannedToolCall(
                    tool_name=tool_definition.name,
                    domain=tool_definition.domain,
                    description=tool_definition.description,
                )
            )

            routing_rule = routing_rules_by_tool_name.get(tool_definition.name)
            if routing_rule is None:
                continue

            if routing_rule.evidence_note:
                evidence.append(routing_rule.evidence_note)

            if routing_rule.privileged_action and routing_rule.fallback_action:
                actions.append(
                    routing_rule.privileged_action
                    if normalized_role in ACTION_ENABLED_ROLES
                    else routing_rule.fallback_action
                )

        return tool_names, planned_tool_calls, evidence, actions

    def plan_tool_calls_with_langchain(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolRegistry,
    ) -> tuple[list[str], list[PlannedToolCall], list[str], list[str]]:
        """Temporary LangChain planner seam with safe fallback to rule routing."""

        planner_payload = self.build_langchain_planner_payload(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
        )
        if self.planner_override_output is not None:
            selected_tool_names = self.extract_tool_names_from_langchain_output(
                planner_output_text=self.planner_override_output,
                registry=registry,
            )
            if selected_tool_names:
                tool_names, planned_tool_calls, evidence, actions = (
                    self.build_tool_plan_from_names(
                        selected_tool_names=selected_tool_names,
                        normalized_role=normalized_role,
                        registry=registry,
                    )
                )
                evidence.append(
                    "Planner override selected tools before registry-backed execution."
                )
                return tool_names, planned_tool_calls, evidence, actions

        planner_model = self.init_langchain_chat_model()

        if planner_model is not None:
            try:
                planner_response = planner_model.invoke(planner_payload["planner_prompt"])
                planner_output_text = str(getattr(planner_response, "content", planner_response))
                selected_tool_names = self.extract_tool_names_from_langchain_output(
                    planner_output_text=planner_output_text,
                    registry=registry,
                )
                if selected_tool_names:
                    tool_names, planned_tool_calls, evidence, actions = (
                        self.build_tool_plan_from_names(
                            selected_tool_names=selected_tool_names,
                            normalized_role=normalized_role,
                            registry=registry,
                        )
                    )
                    evidence.append(
                        "LangChain planner selected tools before registry-backed execution."
                    )
                    return tool_names, planned_tool_calls, evidence, actions
            except Exception:
                pass

        return self.plan_tool_calls(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
        )

    def invoke_planned_tool_calls(
        self,
        normalized_role: str,
        normalized_text: str,
        planned_tool_calls: list[PlannedToolCall],
        registry: ToolRegistry,
    ) -> tuple[list[ToolInvocationResult], list[str]]:
        tool_invocation_results: list[ToolInvocationResult] = []
        evidence: list[str] = []

        if not planned_tool_calls:
            return tool_invocation_results, evidence

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

        return tool_invocation_results, evidence

    def build_sensitive_action_response(
        self,
        normalized_role: str,
        normalized_text: str,
    ) -> AgentResponse | None:
        lowered_text = normalized_text.lower()
        if not any(keyword in lowered_text for keyword in SENSITIVE_ACTION_KEYWORDS):
            return None

        if normalized_role in SENSITIVE_ACTION_ALLOWED_ROLES:
            return None

        return AgentResponse(
            reply_text=(
                "I can summarize the request, but I cannot recommend or initiate "
                "that sensitive action for your current role."
            ),
            actions=["Escalate this request to a supervisor or admin."],
        )

    def build_agent_response(
        self,
        normalized_role: str,
        tool_names: list[str],
        planned_tool_calls: list[PlannedToolCall],
        tool_invocation_results: list[ToolInvocationResult],
        evidence: list[str],
        actions: list[str],
    ) -> AgentResponse:
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

    def handle_chat(self, user_role: str, message_text: str) -> AgentResponse:
        normalized_role = user_role.strip().lower()
        normalized_text = message_text.strip()
        registry = build_default_registry()

        if not normalized_text:
            return AgentResponse(reply_text="Please provide a chat request.")

        sensitive_action_response = self.build_sensitive_action_response(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
        )
        if sensitive_action_response is not None:
            return sensitive_action_response

        tool_names, planned_tool_calls, evidence, actions = self.plan_tool_calls_with_langchain(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
        )
        tool_invocation_results, invocation_evidence = self.invoke_planned_tool_calls(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            planned_tool_calls=planned_tool_calls,
            registry=registry,
        )
        evidence.extend(invocation_evidence)

        return self.build_agent_response(
            normalized_role=normalized_role,
            tool_names=tool_names,
            planned_tool_calls=planned_tool_calls,
            tool_invocation_results=tool_invocation_results,
            evidence=evidence,
            actions=actions,
        )
