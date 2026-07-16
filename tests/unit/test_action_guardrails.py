from backend.agent.models import PlannedToolCall
from backend.agent.service import AgentService
from backend.guardrails.policy import GuardrailPolicy
from backend.mcp_gateway.registry import build_default_registry


def test_guardrail_policy_requires_role_approval_and_grounded_evidence() -> None:
    policy = GuardrailPolicy()

    role_decision = policy.enforce_tool_invocation(
        tool_name="ops.create_alert_or_action",
        normalized_role="analyst",
    )
    assert role_decision.allowed is False
    assert role_decision.reason == "role_not_permitted"

    approval_decision = policy.enforce_tool_invocation(
        tool_name="ops.create_alert_or_action",
        normalized_role="supervisor",
        authorization_context={"approval_status": "pending"},
    )
    assert approval_decision.allowed is False
    assert approval_decision.reason == "approval_required"

    evidence_decision = policy.enforce_tool_invocation(
        tool_name="ops.create_alert_or_action",
        normalized_role="supervisor",
        authorization_context={"approval_status": "approved"},
        evidence_context={"has_grounded_evidence": False},
    )
    assert evidence_decision.allowed is False
    assert evidence_decision.reason == "evidence_required"


def test_guardrail_allows_approved_evidence_bound_action() -> None:
    decision = GuardrailPolicy().enforce_tool_invocation(
        tool_name="ops.create_alert_or_action",
        normalized_role="supervisor",
        authorization_context={"approval_status": "approved"},
        evidence_context={"has_grounded_evidence": True},
    )

    assert decision.allowed is True
    assert decision.reason == "allowed"


def test_agent_blocks_ops_handler_before_registry_invocation() -> None:
    class SpyRegistry:
        def __init__(self) -> None:
            self.registry = build_default_registry()
            self.invoke_count = 0

        def get_tool(self, tool_name: str):
            return self.registry.get_tool(tool_name)

        def list_tool_names(self) -> list[str]:
            return self.registry.list_tool_names()

        def invoke(self, tool_name: str, request_payload=None):
            self.invoke_count += 1
            return self.registry.invoke(tool_name, request_payload)

    registry = SpyRegistry()
    results, evidence = AgentService().invoke_planned_tool_calls(
        normalized_role="analyst",
        normalized_text="Create an alert.",
        planned_tool_calls=[
            PlannedToolCall(
                tool_name="ops.create_alert_or_action",
                domain="operations",
                description="Prepare an alert or follow-up action payload.",
            )
        ],
        registry=registry,
        authorization_context={"approval_status": "approved"},
        evidence_context={"has_grounded_evidence": True},
    )

    assert registry.invoke_count == 0
    assert results[0].invocation_status == "blocked"
    assert results[0].transport == "guardrail"
    assert results[0].response_payload["guardrail"]["reason"] == "role_not_permitted"
    assert evidence == [
        "Tool invocation blocked for ops.create_alert_or_action: role_not_permitted."
    ]
