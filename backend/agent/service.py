import logging
from dataclasses import dataclass, field
from time import perf_counter

from pydantic import ValidationError

from backend.agent.models import (
    AgentResponse,
    ChatCommand,
    ChatHistoryMessage,
    PlannedToolCall,
    PlannerResult,
)
from backend.agent.planning.langchain import (
    DEFAULT_LANGCHAIN_MODEL_NAME,
    DEFAULT_LANGCHAIN_MODEL_PROVIDER,
    DEFAULT_LANGCHAIN_PLANNER_MODE,
    LEGACY_TEXT_PLANNER_MODE,
    LANGCHAIN_MODEL_SOURCE,
    PLANNER_OVERRIDE_SOURCE,
    RULE_FALLBACK_SOURCE,
    STRUCTURED_PLANNER_MODE,
    StructuredPlannerUnavailableError,
    build_planner_source_evidence,
    init_langchain_chat_model,
    invoke_structured_planner,
)
from backend.agent.planning.parser import (
    extract_langchain_planner_output_candidates,
    parse_langchain_planner_output,
)
from backend.agent.planning.prompt import (
    LangChainPlannerConfig,
    build_langchain_guardrail_context_prompt,
    build_langchain_message_history_payload,
    build_langchain_planner_output_contract,
    build_langchain_planner_payload,
    build_langchain_planner_prompt,
    build_langchain_retrieval_context_prompt,
    build_langchain_tool_catalog,
)
from backend.agent.ports import ToolGatewayPort
from backend.guardrails.policy import ACTION_ENABLED_ROLES, GuardrailPolicy
from backend.mcp_gateway.registry import ToolInvocationResult, build_default_registry
from backend.retrieval.contracts import RetrievalQuery
from backend.retrieval.service import RetrievalService
from backend.storage.chat_persistence import ChatPersistenceCoordinator
from backend.storage.redis_chat_context import RedisChatContextStore


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ToolRoutingRule:
    """Centralized placeholder rule for keyword-based tool routing."""

    tool_name: str
    keywords: tuple[str, ...]
    evidence_note: str | None = None
    privileged_action: str | None = None
    fallback_action: str | None = None


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
    planner_override_output: str | None = None
    retrieval_service: RetrievalService = field(default_factory=RetrievalService)
    guardrail_policy: GuardrailPolicy = field(default_factory=GuardrailPolicy)
    chat_persistence_coordinator: ChatPersistenceCoordinator | None = None
    redis_chat_context_store: RedisChatContextStore | None = None

    def describe(self) -> str:
        return (
            "Placeholder agent service. "
            "Tool routing, cache, RAG, and guardrails will be added in later batches."
        )

    def plan_tool_calls(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolGatewayPort,
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
        registry: ToolGatewayPort,
    ) -> list[dict[str, str]]:
        return build_langchain_tool_catalog(registry)

    def build_langchain_planner_prompt(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolGatewayPort,
        retrieval_context: dict[str, object],
        guardrail_context: dict[str, object],
    ) -> str:
        output_contract = self.build_langchain_planner_output_contract(registry)
        return build_langchain_planner_prompt(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            output_contract=output_contract,
            retrieval_context=retrieval_context,
            guardrail_context=guardrail_context,
        )

    def build_langchain_planner_output_contract(
        self,
        registry: ToolGatewayPort,
    ) -> dict[str, object]:
        return build_langchain_planner_output_contract(
            registry=registry,
            fallback_tool=DEFAULT_TOOL_NAME,
        )

    def build_langchain_message_history_payload(
        self,
        session_id: str | None,
        recent_messages: list[ChatHistoryMessage] | None,
        normalized_role: str,
        normalized_text: str,
    ) -> dict[str, object]:
        return build_langchain_message_history_payload(
            session_id=session_id,
            recent_messages=recent_messages,
            normalized_role=normalized_role,
            normalized_text=normalized_text,
        )

    def build_langchain_retrieval_context_payload(
        self,
        normalized_text: str,
        registry: ToolGatewayPort,
    ) -> dict[str, object]:
        retrieve = getattr(self.retrieval_service, "retrieve", None)
        if callable(retrieve):
            try:
                return retrieve(
                    RetrievalQuery(text=normalized_text, top_k=2)
                ).to_payload()
            except RuntimeError:
                # Standalone unit tests may use an intentionally unconfigured service.
                pass
        return self.retrieval_service.build_context(
            normalized_text=normalized_text,
            tool_gateway=registry,
            limit=2,
        ).to_payload()

    def build_langchain_retrieval_context_prompt(
        self,
        retrieval_context: dict[str, object],
    ) -> str:
        return build_langchain_retrieval_context_prompt(retrieval_context)

    def build_langchain_guardrail_context_payload(
        self,
        normalized_role: str,
        normalized_text: str,
    ) -> dict[str, object]:
        return self.guardrail_policy.build_decision(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
        ).to_payload()

    def build_langchain_guardrail_context_prompt(
        self,
        guardrail_context: dict[str, object],
    ) -> str:
        return build_langchain_guardrail_context_prompt(guardrail_context)

    def build_langchain_planner_payload(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolGatewayPort,
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
        return build_langchain_planner_payload(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            planner_config=planner_config,
            tool_catalog=tool_catalog,
            output_contract=output_contract,
            message_history=message_history,
            retrieval_context=retrieval_context,
            guardrail_context=guardrail_context,
        )

    def init_langchain_chat_model(self) -> object | None:
        return init_langchain_chat_model(
            model_name=DEFAULT_LANGCHAIN_MODEL_NAME,
            model_provider=DEFAULT_LANGCHAIN_MODEL_PROVIDER,
        )

    def build_planner_source_evidence(self, planner_source: str) -> str:
        return build_planner_source_evidence(planner_source)

    def extract_langchain_planner_output_candidates(
        self,
        planner_output_text: str,
    ) -> list[str]:
        return extract_langchain_planner_output_candidates(planner_output_text)

    def parse_langchain_planner_output(
        self,
        planner_output_text: str,
        registry: ToolGatewayPort,
    ) -> list[str]:
        output_contract = self.build_langchain_planner_output_contract(registry)
        return parse_langchain_planner_output(
            planner_output_text=planner_output_text,
            allowed_tool_names=output_contract["allowed_tool_names"],
        )

    def build_langchain_planner_result(
        self,
        normalized_role: str,
        normalized_text: str,
        registry: ToolGatewayPort,
        session_id: str | None = None,
        recent_messages: list[ChatHistoryMessage] | None = None,
    ) -> PlannerResult:
        planner_started_at = perf_counter()
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
                    planner_mode="override",
                    latency_ms=self._build_planner_latency_ms(planner_started_at),
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
                planner_decision = invoke_structured_planner(
                    planner_model=planner_model,
                    planner_prompt=planner_payload["planner_prompt"],
                )
                candidate_tool_names = list(planner_decision.selected_tool_names)
                selected_tool_names, unknown_tool_names = (
                    self.parse_structured_planner_decision(
                        planner_decision=planner_decision,
                        registry=registry,
                    )
                )
                if selected_tool_names and not unknown_tool_names:
                    return PlannerResult(
                        planner_source=LANGCHAIN_MODEL_SOURCE,
                        planner_mode=STRUCTURED_PLANNER_MODE,
                        model_provider=DEFAULT_LANGCHAIN_MODEL_PROVIDER,
                        model_name=DEFAULT_LANGCHAIN_MODEL_NAME,
                        latency_ms=self._build_planner_latency_ms(planner_started_at),
                        raw_output_text=planner_decision.model_dump_json(),
                        candidate_tool_names=candidate_tool_names,
                        selected_tool_names=selected_tool_names,
                    )

                fallback_reason = (
                    "empty_selection"
                    if not candidate_tool_names
                    else "invalid_tool_selection"
                )
                fallback_raw_output_text = planner_decision.model_dump_json()
                fallback_candidate_tool_names = candidate_tool_names
            except StructuredPlannerUnavailableError:
                try:
                    planner_response = planner_model.invoke(
                        planner_payload["planner_prompt"]
                    )
                    planner_output_text = str(
                        getattr(planner_response, "content", planner_response)
                    )
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
                            planner_mode=LEGACY_TEXT_PLANNER_MODE,
                            model_provider=DEFAULT_LANGCHAIN_MODEL_PROVIDER,
                            model_name=DEFAULT_LANGCHAIN_MODEL_NAME,
                            latency_ms=self._build_planner_latency_ms(planner_started_at),
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
            except ValidationError:
                fallback_reason = "schema_validation_failed"
                fallback_raw_output_text = None
                fallback_candidate_tool_names = []
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
            planner_mode=RULE_FALLBACK_SOURCE,
            model_provider=DEFAULT_LANGCHAIN_MODEL_PROVIDER,
            model_name=DEFAULT_LANGCHAIN_MODEL_NAME,
            latency_ms=self._build_planner_latency_ms(planner_started_at),
            raw_output_text=fallback_raw_output_text,
            candidate_tool_names=fallback_candidate_tool_names,
            selected_tool_names=fallback_tool_names,
            used_fallback=True,
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def _build_planner_latency_ms(started_at: float) -> int:
        return max(0, round((perf_counter() - started_at) * 1000))

    @staticmethod
    def parse_structured_planner_decision(
        planner_decision,
        registry: ToolGatewayPort,
    ) -> tuple[list[str], list[str]]:
        allowed_tool_names_by_lower = {
            tool_name.lower(): tool_name for tool_name in registry.list_tool_names()
        }
        selected_tool_names: list[str] = []
        unknown_tool_names: list[str] = []
        seen_tool_names: set[str] = set()
        for candidate_tool_name in planner_decision.selected_tool_names:
            normalized_candidate = candidate_tool_name.strip()
            canonical_tool_name = allowed_tool_names_by_lower.get(
                normalized_candidate.lower()
            )
            if canonical_tool_name is None:
                unknown_tool_names.append(normalized_candidate)
                continue
            if canonical_tool_name in seen_tool_names:
                continue
            seen_tool_names.add(canonical_tool_name)
            selected_tool_names.append(canonical_tool_name)
        return selected_tool_names, unknown_tool_names

    def build_tool_plan_from_names(
        self,
        selected_tool_names: list[str],
        normalized_role: str,
        registry: ToolGatewayPort,
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
        registry: ToolGatewayPort,
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
        logger.info(
            "Planner execution completed",
            extra={
                "planner_source": planner_result.planner_source,
                "planner_mode": planner_result.planner_mode,
                "model_provider": planner_result.model_provider,
                "model_name": planner_result.model_name,
                "latency_ms": planner_result.latency_ms,
                "fallback_reason": planner_result.fallback_reason,
                "selected_tool_count": len(planner_result.selected_tool_names),
            },
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
        registry: ToolGatewayPort,
        authorization_context: dict[str, object] | None = None,
    ) -> tuple[list[ToolInvocationResult], list[str]]:
        tool_invocation_results: list[ToolInvocationResult] = []
        evidence: list[str] = []

        if not planned_tool_calls:
            return tool_invocation_results, evidence

        request_payload = {
            "user_role": normalized_role or "unknown",
            "message_text": normalized_text,
        }
        if authorization_context is not None:
            request_payload["authorization_context"] = authorization_context
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
        return self.guardrail_policy.build_sensitive_action_response(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
        )

    def build_agent_response(
        self,
        normalized_role: str,
        session_id: str | None,
        tool_names: list[str],
        planned_tool_calls: list[PlannedToolCall],
        tool_invocation_results: list[ToolInvocationResult],
        evidence: list[str],
        actions: list[str],
        planner_result: PlannerResult | None = None,
    ) -> AgentResponse:
        citations = self._extract_retrieval_citations(tool_invocation_results)
        response_evidence = list(evidence)
        if citations:
            response_evidence.append(
                f"Evidence grounded by {len(citations)} knowledge citation(s)."
            )
        return AgentResponse(
            reply_text=(
                f"Prepared a placeholder agent response for the {normalized_role or 'unknown'} "
                "role. The API layer can route this into LangChain and registry-backed MCP "
                "execution next."
            ),
            session_id=session_id,
            tool_names=tool_names,
            planned_tool_calls=planned_tool_calls,
            tool_invocation_results=tool_invocation_results,
            evidence=response_evidence,
            actions=actions,
            planner_result=planner_result,
            citations=citations,
        )

    @staticmethod
    def _extract_retrieval_citations(
        tool_invocation_results: list[ToolInvocationResult],
    ) -> list[dict[str, object]]:
        citations: list[dict[str, object]] = []
        seen_citations: set[tuple[object, ...]] = set()
        for result in tool_invocation_results:
            if result.tool_name != "knowledge.search":
                continue
            raw_citations = result.response_payload.get("citations")
            if not isinstance(raw_citations, list):
                continue
            for raw_citation in raw_citations:
                if not isinstance(raw_citation, dict):
                    continue
                document_id = raw_citation.get("document_id")
                title = raw_citation.get("title")
                if not isinstance(document_id, str) or not isinstance(title, str):
                    continue
                citation = {
                    "document_id": document_id,
                    "title": title,
                    "chunk_id": raw_citation.get("chunk_id"),
                    "chunk_index": raw_citation.get("chunk_index"),
                    "source_path": raw_citation.get("source_path"),
                    "score": raw_citation.get("score"),
                    "excerpt": raw_citation.get("excerpt"),
                }
                citation_key = (
                    citation["document_id"],
                    citation["chunk_id"],
                    citation["source_path"],
                    citation["chunk_index"],
                )
                if citation_key in seen_citations:
                    continue
                seen_citations.add(citation_key)
                citations.append(citation)
        return citations

    def handle_command(
        self,
        command: ChatCommand,
        registry: ToolGatewayPort | None = None,
    ) -> AgentResponse:
        normalized_role = command.user_role.strip().lower()
        normalized_text = command.message_text.strip()
        active_registry = registry or build_default_registry()
        effective_recent_messages = list(command.recent_messages)

        if (
            not effective_recent_messages
            and command.session_id is not None
            and self.redis_chat_context_store is not None
        ):
            if command.user_id is None:
                effective_recent_messages = self.redis_chat_context_store.load_recent_messages(
                    session_id=command.session_id,
                    limit=6,
                )
            else:
                effective_recent_messages = self.redis_chat_context_store.load_recent_messages(
                    session_id=command.session_id,
                    limit=6,
                    user_id=command.user_id,
                )

        if not normalized_text:
            return AgentResponse(reply_text="Please provide a chat request.")

        persistence_exchange = None
        active_session_id = command.session_id
        if self.chat_persistence_coordinator is not None:
            persistence_exchange = self.chat_persistence_coordinator.start_exchange(
                command=command,
                normalized_role=normalized_role,
                normalized_text=normalized_text,
            )
            active_session_id = persistence_exchange.effective_session_id

        sensitive_action_response = self.build_sensitive_action_response(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
        )
        if sensitive_action_response is not None:
            sensitive_action_response.session_id = active_session_id
            if persistence_exchange is not None:
                self.chat_persistence_coordinator.finish_exchange(
                    exchange=persistence_exchange,
                    agent_response=sensitive_action_response,
                )
            return sensitive_action_response

        tool_names, planned_tool_calls, evidence, actions, planner_result = (
            self.plan_tool_calls_with_langchain(
                normalized_role=normalized_role,
                normalized_text=normalized_text,
                registry=active_registry,
                session_id=active_session_id,
                recent_messages=effective_recent_messages,
            )
        )
        tool_invocation_results, invocation_evidence = self.invoke_planned_tool_calls(
            normalized_role=normalized_role,
            normalized_text=normalized_text,
            planned_tool_calls=planned_tool_calls,
            registry=active_registry,
            authorization_context=command.authorization_context,
        )
        evidence.extend(invocation_evidence)

        agent_response = self.build_agent_response(
            normalized_role=normalized_role,
            session_id=active_session_id,
            tool_names=tool_names,
            planned_tool_calls=planned_tool_calls,
            tool_invocation_results=tool_invocation_results,
            evidence=evidence,
            actions=actions,
            planner_result=planner_result,
        )
        if persistence_exchange is not None:
            self.chat_persistence_coordinator.finish_exchange(
                exchange=persistence_exchange,
                agent_response=agent_response,
            )
        return agent_response

    def handle_chat(
        self,
        user_role: str,
        message_text: str,
        session_id: str | None = None,
        recent_messages: list[ChatHistoryMessage] | None = None,
    ) -> AgentResponse:
        return self.handle_command(
            ChatCommand(
                user_role=user_role,
                message_text=message_text,
                session_id=session_id,
                recent_messages=list(recent_messages or []),
            )
        )
