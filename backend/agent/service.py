import re
from dataclasses import dataclass, field

from backend.mcp_gateway.registry import ToolInvocationResult, ToolRegistry, build_default_registry


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
class AgentResponse:
    """Structured placeholder response for the future chat workflow."""

    reply_text: str
    tool_names: list[str] = field(default_factory=list)
    planned_tool_calls: list[PlannedToolCall] = field(default_factory=list)
    tool_invocation_results: list[ToolInvocationResult] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    planner_result: "PlannerResult | None" = None


@dataclass(slots=True)
class PlannerResult:
    """Structured planner trace for the current LangChain selection path."""

    planner_source: str
    raw_output_text: str | None = None
    candidate_tool_names: list[str] = field(default_factory=list)
    selected_tool_names: list[str] = field(default_factory=list)
    used_fallback: bool = False
    fallback_reason: str | None = None


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
PLANNER_OVERRIDE_SOURCE = "planner_override"
LANGCHAIN_MODEL_SOURCE = "langchain_model"
RULE_FALLBACK_SOURCE = "rule_fallback"


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
        retrieval_context: dict[str, object],
        guardrail_context: dict[str, object],
    ) -> str:
        output_contract = self.build_langchain_planner_output_contract(registry)
        available_tool_names = ", ".join(output_contract["allowed_tool_names"])
        retrieval_context_prompt = self.build_langchain_retrieval_context_prompt(
            retrieval_context
        )
        guardrail_context_prompt = self.build_langchain_guardrail_context_prompt(
            guardrail_context
        )
        return (
            "You are the trading and risk operations planner. "
            "Select the best matching tools from the available tool list. "
            "Return only tool names that appear in the allowed tool list. "
            f"Output contract: format={output_contract['format']}; "
            f"allow_multiple={output_contract['allow_multiple']}; "
            f"fallback_tool={output_contract['fallback_tool']}. "
            f"User role: {normalized_role or 'unknown'}. "
            f"Available tools: {available_tool_names}. "
            f"{retrieval_context_prompt} "
            f"{guardrail_context_prompt} "
            f"User request: {normalized_text}"
        )

    def build_langchain_planner_output_contract(
        self,
        registry: ToolRegistry,
    ) -> dict[str, object]:
        return {
            "format": "comma-separated tool names",
            "allow_multiple": True,
            "allowed_tool_names": registry.list_tool_names(),
            "fallback_tool": DEFAULT_TOOL_NAME,
        }

    def build_langchain_message_history_payload(
        self,
        session_id: str | None,
        recent_messages: list[ChatHistoryMessage] | None,
        normalized_role: str,
        normalized_text: str,
    ) -> dict[str, object]:
        messages: list[dict[str, str]] = []
        for recent_message in recent_messages or []:
            normalized_message_role = recent_message.role.strip().lower()
            normalized_message_content = recent_message.content.strip()
            if not normalized_message_content:
                continue
            messages.append(
                {
                    "role": normalized_message_role or "unknown",
                    "content": normalized_message_content,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": normalized_text,
                "actor_role": normalized_role or "unknown",
            }
        )

        return {
            "session_id": session_id,
            "history_source": "request_messages" if recent_messages else "current_turn_only",
            "messages": messages,
        }

    def build_langchain_retrieval_context_payload(
        self,
        normalized_text: str,
        registry: ToolRegistry,
    ) -> dict[str, object]:
        matched_records = registry.preview_knowledge_matches(
            query_text=normalized_text,
            limit=2,
        )
        if not matched_records:
            return {
                "rag_enabled": False,
                "retrieval_source": "knowledge_preview",
                "retrieved_chunks": [],
                "citations": [],
            }

        return {
            "rag_enabled": True,
            "retrieval_source": "knowledge_preview",
            "retrieved_chunks": [
                {
                    "document_id": match["document_id"],
                    "title": match["title"],
                    "summary": match["summary"],
                    "matched_terms": match["matched_terms"],
                }
                for match in matched_records
            ],
            "citations": [
                {
                    "document_id": match["document_id"],
                    "title": match["title"],
                }
                for match in matched_records
            ],
        }

    def build_langchain_retrieval_context_prompt(
        self,
        retrieval_context: dict[str, object],
    ) -> str:
        if not retrieval_context.get("rag_enabled"):
            return "Retrieval context: none."

        retrieved_chunks = retrieval_context.get("retrieved_chunks", [])
        retrieval_lines = []
        for retrieved_chunk in retrieved_chunks:
            retrieval_lines.append(
                f"{retrieved_chunk['title']}: {retrieved_chunk['summary']}"
            )

        return "Retrieval context: " + " | ".join(retrieval_lines)

    def build_langchain_guardrail_context_payload(
        self,
        normalized_role: str,
        normalized_text: str,
    ) -> dict[str, object]:
        lowered_text = normalized_text.lower()
        input_checks: list[str] = []
        output_constraints: list[str] = []
        escalation_required = False

        if any(keyword in lowered_text for keyword in SENSITIVE_ACTION_KEYWORDS):
            input_checks.append("sensitive_action_requested")
            if normalized_role not in SENSITIVE_ACTION_ALLOWED_ROLES:
                output_constraints.append("do_not_initiate_sensitive_actions")
                output_constraints.append("respond_with_escalation_guidance")
                escalation_required = True

        ops_action_requested = any(
            routing_rule.privileged_action and any(keyword in lowered_text for keyword in routing_rule.keywords)
            for routing_rule in TOOL_ROUTING_RULES
        )
        if ops_action_requested:
            input_checks.append("ops_action_requested")
            if normalized_role not in ACTION_ENABLED_ROLES:
                output_constraints.append("do_not_execute_privileged_ops_actions")
                output_constraints.append("limit_response_to_draft_or_summary")
                escalation_required = True

        allowed_action_scope = "analysis_only"
        if normalized_role in ACTION_ENABLED_ROLES:
            allowed_action_scope = "ops_actions_enabled"
        if normalized_role in SENSITIVE_ACTION_ALLOWED_ROLES:
            allowed_action_scope = "sensitive_actions_enabled"

        return {
            "user_role": normalized_role or "unknown",
            "input_checks": input_checks,
            "output_constraints": output_constraints,
            "allowed_action_scope": allowed_action_scope,
            "escalation_required": escalation_required,
        }

    def build_langchain_guardrail_context_prompt(
        self,
        guardrail_context: dict[str, object],
    ) -> str:
        input_checks = guardrail_context.get("input_checks", [])
        output_constraints = guardrail_context.get("output_constraints", [])
        allowed_action_scope = guardrail_context.get("allowed_action_scope", "analysis_only")
        escalation_required = guardrail_context.get("escalation_required", False)

        checks_summary = ", ".join(input_checks) if input_checks else "none"
        constraints_summary = ", ".join(output_constraints) if output_constraints else "none"
        escalation_summary = "required" if escalation_required else "not_required"
        return (
            "Guardrail context: "
            f"scope={allowed_action_scope}; "
            f"input_checks={checks_summary}; "
            f"output_constraints={constraints_summary}; "
            f"escalation={escalation_summary}."
        )

    def build_langchain_planner_payload(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolRegistry,
        session_id: str | None = None,
        recent_messages: list[ChatHistoryMessage] | None = None,
    ) -> dict[str, object]:
        planner_config = self.build_langchain_planner_config()
        tool_catalog = self.build_langchain_tool_catalog(registry)
        output_contract = self.build_langchain_planner_output_contract(registry)
        message_history = self.build_langchain_message_history_payload(
            session_id=session_id,
            recent_messages=recent_messages,
            normalized_role=normalized_role,
            normalized_text=normalized_text,
        )
        retrieval_context = self.build_langchain_retrieval_context_payload(
            normalized_text=normalized_text,
            registry=registry,
        )
        guardrail_context = self.build_langchain_guardrail_context_payload(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
        )
        planner_prompt = self.build_langchain_planner_prompt(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
            retrieval_context=retrieval_context,
            guardrail_context=guardrail_context,
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
            "output_contract": output_contract,
            "message_history": message_history,
            "retrieval_context": retrieval_context,
            "guardrail_context": guardrail_context,
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

    def build_planner_source_evidence(self, planner_source: str) -> str:
        source_evidence_by_name = {
            PLANNER_OVERRIDE_SOURCE: "Planner source: override output.",
            LANGCHAIN_MODEL_SOURCE: "Planner source: LangChain model output.",
            RULE_FALLBACK_SOURCE: "Planner source: keyword fallback routing.",
        }
        return source_evidence_by_name.get(
            planner_source,
            "Planner source: unspecified routing path.",
        )

    def extract_langchain_planner_output_candidates(
        self,
        planner_output_text: str,
    ) -> list[str]:
        candidate_chunks = re.split(r"[,;\n|]+", planner_output_text)
        normalized_candidates: list[str] = []
        for candidate_chunk in candidate_chunks:
            normalized_candidate = candidate_chunk.strip().strip("`*[](){}- ")
            if not normalized_candidate:
                continue
            normalized_candidates.append(normalized_candidate)

        return normalized_candidates

    def parse_langchain_planner_output(
        self,
        planner_output_text: str,
        registry: ToolRegistry,
    ) -> list[str]:
        """Parse free-text planner output into registry-recognized tool names."""
        output_contract = self.build_langchain_planner_output_contract(registry)
        allowed_tool_names = output_contract["allowed_tool_names"]
        allowed_tool_names_by_lower = {
            tool_name.lower(): tool_name for tool_name in allowed_tool_names
        }
        candidate_tool_names = self.extract_langchain_planner_output_candidates(
            planner_output_text
        )
        selected_tool_names: list[str] = []
        seen_tool_names: set[str] = set()

        for candidate_tool_name in candidate_tool_names:
            normalized_tool_name = allowed_tool_names_by_lower.get(
                candidate_tool_name.lower()
            )
            if normalized_tool_name is None:
                continue
            if normalized_tool_name in seen_tool_names:
                continue

            seen_tool_names.add(normalized_tool_name)
            selected_tool_names.append(normalized_tool_name)

        return selected_tool_names

    def build_langchain_planner_result(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolRegistry,
        session_id: str | None = None,
        recent_messages: list[ChatHistoryMessage] | None = None,
    ) -> PlannerResult:
        planner_payload = self.build_langchain_planner_payload(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
            session_id=session_id,
            recent_messages=recent_messages,
        )

        if self.planner_override_output is not None:
            candidate_tool_names = self.extract_langchain_planner_output_candidates(
                self.planner_override_output
            )
            selected_tool_names = self.parse_langchain_planner_output(
                planner_output_text=self.planner_override_output,
                registry=registry,
            )
            if selected_tool_names:
                return PlannerResult(
                    planner_source=PLANNER_OVERRIDE_SOURCE,
                    raw_output_text=self.planner_override_output,
                    candidate_tool_names=candidate_tool_names,
                    selected_tool_names=selected_tool_names,
                )

        planner_model = self.init_langchain_chat_model()
        fallback_reason = "planner_model_unavailable"
        fallback_raw_output_text: str | None = self.planner_override_output
        fallback_candidate_tool_names: list[str] = []

        if planner_model is not None:
            try:
                planner_response = planner_model.invoke(planner_payload["planner_prompt"])
                planner_output_text = str(getattr(planner_response, "content", planner_response))
                candidate_tool_names = self.extract_langchain_planner_output_candidates(
                    planner_output_text
                )
                selected_tool_names = self.parse_langchain_planner_output(
                    planner_output_text=planner_output_text,
                    registry=registry,
                )
                if selected_tool_names:
                    return PlannerResult(
                        planner_source=LANGCHAIN_MODEL_SOURCE,
                        raw_output_text=planner_output_text,
                        candidate_tool_names=candidate_tool_names,
                        selected_tool_names=selected_tool_names,
                    )

                fallback_reason = "langchain_output_unusable"
                fallback_raw_output_text = planner_output_text
                fallback_candidate_tool_names = candidate_tool_names
            except Exception:
                fallback_reason = "planner_invoke_failed"
                fallback_raw_output_text = None
                fallback_candidate_tool_names = []

        fallback_tool_names, _, _, _ = self.plan_tool_calls(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
        )
        return PlannerResult(
            planner_source=RULE_FALLBACK_SOURCE,
            raw_output_text=fallback_raw_output_text,
            candidate_tool_names=fallback_candidate_tool_names,
            selected_tool_names=fallback_tool_names,
            used_fallback=True,
            fallback_reason=fallback_reason,
        )

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
        session_id: str | None = None,
        recent_messages: list[ChatHistoryMessage] | None = None,
    ) -> tuple[list[str], list[PlannedToolCall], list[str], list[str], PlannerResult]:
        """Temporary LangChain planner seam with safe fallback to rule routing."""

        planner_result = self.build_langchain_planner_result(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            registry=registry,
            session_id=session_id,
            recent_messages=recent_messages,
        )

        if planner_result.used_fallback:
            tool_names, planned_tool_calls, evidence, actions = self.plan_tool_calls(
                normalized_role=normalized_role,
                normalized_text=normalized_text,
                registry=registry,
            )
            evidence.append(self.build_planner_source_evidence(RULE_FALLBACK_SOURCE))
            if planner_result.fallback_reason is not None:
                evidence.append(
                    f"Planner fallback reason: {planner_result.fallback_reason}."
                )
            return tool_names, planned_tool_calls, evidence, actions, planner_result

        tool_names, planned_tool_calls, evidence, actions = self.build_tool_plan_from_names(
            selected_tool_names=planner_result.selected_tool_names,
            normalized_role=normalized_role,
            registry=registry,
        )

        if planner_result.planner_source == PLANNER_OVERRIDE_SOURCE:
            evidence.append(self.build_planner_source_evidence(PLANNER_OVERRIDE_SOURCE))
            evidence.append(
                "Planner override selected tools before registry-backed execution."
            )
        elif planner_result.planner_source == LANGCHAIN_MODEL_SOURCE:
            evidence.append(
                "LangChain planner selected tools before registry-backed execution."
            )
            evidence.append(self.build_planner_source_evidence(LANGCHAIN_MODEL_SOURCE))

        return tool_names, planned_tool_calls, evidence, actions, planner_result

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
        planner_result: PlannerResult | None = None,
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
            planner_result=planner_result,
        )

    def handle_chat(
        self,
        user_role: str,
        message_text: str,
        session_id: str | None = None,
        recent_messages: list[ChatHistoryMessage] | None = None,
    ) -> AgentResponse:
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

        tool_names, planned_tool_calls, evidence, actions, planner_result = (
            self.plan_tool_calls_with_langchain(
                normalized_role=normalized_role,
                normalized_text=normalized_text,
                registry=registry,
                session_id=session_id,
                recent_messages=recent_messages,
            )
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
            planner_result=planner_result,
        )
