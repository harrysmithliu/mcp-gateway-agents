from dataclasses import dataclass

from backend.agent.models import ChatHistoryMessage
from backend.agent.ports import ToolGatewayPort


@dataclass(frozen=True, slots=True)
class LangChainPlannerConfig:
    """Placeholder planner config before LangChain model wiring is enabled."""

    package_name: str
    model_provider: str
    model_name: str
    planner_mode: str


def build_langchain_tool_catalog(
    registry: ToolGatewayPort,
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


def build_langchain_planner_output_contract(
    registry: ToolGatewayPort,
    fallback_tool: str,
) -> dict[str, object]:
    return {
        "format": "comma-separated tool names",
        "allow_multiple": True,
        "allowed_tool_names": registry.list_tool_names(),
        "fallback_tool": fallback_tool,
    }


def build_langchain_message_history_payload(
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


def build_langchain_retrieval_context_prompt(
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


def build_langchain_guardrail_context_prompt(
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


def build_langchain_planner_prompt(
    normalized_role: str,
    normalized_text: str,
    output_contract: dict[str, object],
    retrieval_context: dict[str, object],
    guardrail_context: dict[str, object],
) -> str:
    available_tool_names = ", ".join(output_contract["allowed_tool_names"])
    retrieval_context_prompt = build_langchain_retrieval_context_prompt(
        retrieval_context
    )
    guardrail_context_prompt = build_langchain_guardrail_context_prompt(
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


def build_langchain_planner_payload(
    normalized_role: str,
    normalized_text: str,
    planner_config: LangChainPlannerConfig,
    tool_catalog: list[dict[str, str]],
    output_contract: dict[str, object],
    message_history: dict[str, object],
    retrieval_context: dict[str, object],
    guardrail_context: dict[str, object],
) -> dict[str, object]:
    planner_prompt = build_langchain_planner_prompt(
        normalized_role=normalized_role,
        normalized_text=normalized_text,
        output_contract=output_contract,
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
