from dataclasses import dataclass, field
from typing import Mapping

from backend.agent.models import AgentResponse

SENSITIVE_ACTION_KEYWORDS = ("freeze", "release", "unlock")
SENSITIVE_ACTION_ALLOWED_ROLES = frozenset({"supervisor", "admin"})
ACTION_ENABLED_ROLES = frozenset({"risk_operator", "supervisor", "admin"})
OPS_ACTION_KEYWORDS = ("alert", "review", "escalate")
HIGH_IMPACT_TOOL_NAMES = frozenset({"ops.create_alert_or_action"})


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    user_role: str
    input_checks: list[str] = field(default_factory=list)
    output_constraints: list[str] = field(default_factory=list)
    allowed_action_scope: str = "analysis_only"
    escalation_required: bool = False

    def to_payload(self) -> dict[str, object]:
        return {
            "user_role": self.user_role,
            "input_checks": list(self.input_checks),
            "output_constraints": list(self.output_constraints),
            "allowed_action_scope": self.allowed_action_scope,
            "escalation_required": self.escalation_required,
        }


@dataclass(frozen=True, slots=True)
class ToolEnforcementDecision:
    """Pre-invocation decision for a potentially high-impact tool."""

    tool_name: str
    allowed: bool
    reason: str
    required_approval: bool = False
    approval_status: str = "not_provided"
    evidence_required: bool = False
    evidence_present: bool = False

    def to_payload(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "allowed": self.allowed,
            "reason": self.reason,
            "required_approval": self.required_approval,
            "approval_status": self.approval_status,
            "evidence_required": self.evidence_required,
            "evidence_present": self.evidence_present,
        }


@dataclass(slots=True)
class GuardrailPolicy:
    """Placeholder for future response and action checks."""

    require_evidence_for_sensitive_actions: bool = True
    block_unapproved_high_impact_actions: bool = True
    require_approval_for_high_impact_tools: bool = True
    require_evidence_for_high_impact_tools: bool = True

    def enforce_tool_invocation(
        self,
        tool_name: str,
        normalized_role: str,
        authorization_context: Mapping[str, object] | None = None,
        evidence_context: Mapping[str, object] | None = None,
    ) -> ToolEnforcementDecision:
        """Enforce action permissions before any registry handler is called."""

        if tool_name not in HIGH_IMPACT_TOOL_NAMES:
            return ToolEnforcementDecision(
                tool_name=tool_name,
                allowed=True,
                reason="not_high_impact",
            )

        if normalized_role not in ACTION_ENABLED_ROLES:
            return ToolEnforcementDecision(
                tool_name=tool_name,
                allowed=False,
                reason="role_not_permitted",
            )

        authorization_context = authorization_context or {}
        approval_status = str(
            authorization_context.get("approval_status", "not_provided")
        ).strip().lower()
        if self.require_approval_for_high_impact_tools and approval_status != "approved":
            return ToolEnforcementDecision(
                tool_name=tool_name,
                allowed=False,
                reason="approval_required",
                required_approval=True,
                approval_status=approval_status,
            )

        evidence_context = evidence_context or {}
        evidence_present = bool(evidence_context.get("has_grounded_evidence", False))
        if self.require_evidence_for_high_impact_tools and not evidence_present:
            return ToolEnforcementDecision(
                tool_name=tool_name,
                allowed=False,
                reason="evidence_required",
                required_approval=self.require_approval_for_high_impact_tools,
                approval_status=approval_status,
                evidence_required=self.require_evidence_for_high_impact_tools,
                evidence_present=False,
            )

        return ToolEnforcementDecision(
            tool_name=tool_name,
            allowed=True,
            reason="allowed",
            required_approval=self.require_approval_for_high_impact_tools,
            approval_status=approval_status,
            evidence_required=self.require_evidence_for_high_impact_tools,
            evidence_present=True,
        )

    def build_decision(
        self,
        normalized_role: str,
        normalized_text: str,
    ) -> GuardrailDecision:
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

        if any(keyword in lowered_text for keyword in OPS_ACTION_KEYWORDS):
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

        return GuardrailDecision(
            user_role=normalized_role or "unknown",
            input_checks=input_checks,
            output_constraints=output_constraints,
            allowed_action_scope=allowed_action_scope,
            escalation_required=escalation_required,
        )

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
