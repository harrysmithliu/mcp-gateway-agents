import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.service import AgentService
from backend.guardrails.policy import GuardrailPolicy
from backend.mcp_gateway.registry import build_default_registry
from backend.retrieval.service import RetrievalService


def test_retrieval_service_builds_typed_context_with_matches() -> None:
    retrieval_service = RetrievalService()
    registry = build_default_registry()

    retrieval_context = retrieval_service.build_context(
        normalized_text="Search policy evidence for suspicious trade exposure.",
        tool_gateway=registry,
        limit=2,
    )

    assert retrieval_context.rag_enabled is True
    assert retrieval_context.retrieval_source == "knowledge_preview"
    assert retrieval_context.retrieved_chunks
    assert retrieval_context.citations
    assert retrieval_context.retrieved_chunks[0].title


def test_retrieval_service_returns_empty_typed_context_when_no_matches() -> None:
    retrieval_service = RetrievalService()
    registry = build_default_registry()

    retrieval_context = retrieval_service.build_context(
        normalized_text="unmatched-term-xyz",
        tool_gateway=registry,
        limit=2,
    )

    assert retrieval_context.rag_enabled is False
    assert retrieval_context.retrieved_chunks == []
    assert retrieval_context.citations == []


def test_guardrail_policy_builds_typed_decision_for_sensitive_ops_request() -> None:
    guardrail_policy = GuardrailPolicy()

    guardrail_decision = guardrail_policy.build_decision(
        normalized_role="analyst",
        normalized_text="Please freeze this account and create an alert.",
    )

    assert guardrail_decision.user_role == "analyst"
    assert guardrail_decision.allowed_action_scope == "analysis_only"
    assert guardrail_decision.escalation_required is True
    assert "sensitive_action_requested" in guardrail_decision.input_checks
    assert "ops_action_requested" in guardrail_decision.input_checks
    assert "do_not_initiate_sensitive_actions" in guardrail_decision.output_constraints


def test_guardrail_policy_builds_sensitive_action_response_for_blocked_role() -> None:
    guardrail_policy = GuardrailPolicy()

    blocked_response = guardrail_policy.build_sensitive_action_response(
        normalized_role="analyst",
        normalized_text="Please freeze this account.",
    )

    assert blocked_response is not None
    assert "cannot recommend or initiate" in blocked_response.reply_text
    assert blocked_response.actions == ["Escalate this request to a supervisor or admin."]


def test_agent_service_uses_injected_retrieval_and_guardrail_services() -> None:
    class FakeRetrievalService:
        def build_context(self, normalized_text: str, tool_gateway, limit: int = 2):
            class FakeContext:
                rag_enabled = True
                retrieval_source = "fake"
                retrieved_chunks = []
                citations = []

                def to_payload(self) -> dict[str, object]:
                    return {
                        "rag_enabled": True,
                        "retrieval_source": "fake",
                        "retrieved_chunks": [],
                        "citations": [],
                    }

            return FakeContext()

    class FakeGuardrailPolicy:
        def build_decision(self, normalized_role: str, normalized_text: str):
            class FakeDecision:
                def to_payload(self) -> dict[str, object]:
                    return {
                        "user_role": normalized_role,
                        "input_checks": ["fake_check"],
                        "output_constraints": [],
                        "allowed_action_scope": "analysis_only",
                        "escalation_required": False,
                    }

            return FakeDecision()

        def build_sensitive_action_response(
            self,
            normalized_role: str,
            normalized_text: str,
        ):
            return None

    agent_service = AgentService(
        retrieval_service=FakeRetrievalService(),
        guardrail_policy=FakeGuardrailPolicy(),
    )
    registry = build_default_registry()

    retrieval_context = agent_service.build_langchain_retrieval_context_payload(
        normalized_text="Search policy evidence.",
        registry=registry,
    )
    guardrail_context = agent_service.build_langchain_guardrail_context_payload(
        normalized_role="analyst",
        normalized_text="Search policy evidence.",
    )

    assert retrieval_context["retrieval_source"] == "fake"
    assert guardrail_context["input_checks"] == ["fake_check"]
