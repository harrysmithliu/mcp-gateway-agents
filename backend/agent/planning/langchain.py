from typing import Any

from backend.agent.planning.contracts import PlannerDecision


DEFAULT_LANGCHAIN_MODEL_PROVIDER = "anthropic"
DEFAULT_LANGCHAIN_MODEL_NAME = "claude-3-5-sonnet"
DEFAULT_LANGCHAIN_PLANNER_MODE = "tool-routing-placeholder"
PLANNER_OVERRIDE_SOURCE = "planner_override"
LANGCHAIN_MODEL_SOURCE = "langchain_model"
RULE_FALLBACK_SOURCE = "rule_fallback"
STRUCTURED_PLANNER_MODE = "structured"
LEGACY_TEXT_PLANNER_MODE = "legacy_text"


class StructuredPlannerUnavailableError(RuntimeError):
    """Raised when a model does not expose LangChain structured output support."""


def init_langchain_chat_model(
    model_name: str = DEFAULT_LANGCHAIN_MODEL_NAME,
    model_provider: str = DEFAULT_LANGCHAIN_MODEL_PROVIDER,
) -> object | None:
    try:
        from langchain.chat_models import init_chat_model
    except ImportError:
        return None

    try:
        return init_chat_model(
            model_name,
            model_provider=model_provider,
        )
    except Exception:
        return None


def invoke_structured_planner(
    planner_model: Any,
    planner_prompt: str,
) -> PlannerDecision:
    """Invoke a LangChain model through the typed PlannerDecision schema."""

    with_structured_output = getattr(planner_model, "with_structured_output", None)
    if not callable(with_structured_output):
        raise StructuredPlannerUnavailableError(
            "planner model does not support with_structured_output"
        )

    structured_model = with_structured_output(PlannerDecision)
    structured_response = structured_model.invoke(planner_prompt)
    if isinstance(structured_response, PlannerDecision):
        return structured_response
    return PlannerDecision.model_validate(structured_response)


def build_planner_source_evidence(planner_source: str) -> str:
    source_evidence_by_name = {
        PLANNER_OVERRIDE_SOURCE: "Planner source: override output.",
        LANGCHAIN_MODEL_SOURCE: "Planner source: LangChain model output.",
        RULE_FALLBACK_SOURCE: "Planner source: keyword fallback routing.",
    }
    return source_evidence_by_name.get(
        planner_source,
        "Planner source: unspecified routing path.",
    )
