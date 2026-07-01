from dataclasses import dataclass


@dataclass(slots=True)
class GuardrailPolicy:
    """Phase 1 placeholder for future response and action checks."""

    require_evidence_for_sensitive_actions: bool = True
    block_unapproved_high_impact_actions: bool = True

