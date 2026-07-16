from dataclasses import dataclass
from enum import StrEnum

from backend.mcp_gateway.knowledge import is_knowledge_result_usable
from backend.mcp_gateway.models import ToolInvocationResult


class EvidenceGuardrailStatus(StrEnum):
    """Stable deterministic outcome for evidence-bound output validation."""

    NOT_APPLICABLE = "not_applicable"
    GROUNDED = "grounded"
    NO_GROUNDING = "no_grounding"
    DOWNGRADED = "downgraded"


@dataclass(frozen=True, slots=True)
class EvidenceGuardrailResult:
    """Validated citations and evidence text for one agent response."""

    status: EvidenceGuardrailStatus
    citations: list[dict[str, object]]
    evidence: list[str]
    reason: str | None = None


def validate_evidence_bound_output(
    tool_invocation_results: list[ToolInvocationResult],
    citations: list[dict[str, object]],
    evidence: list[str],
) -> EvidenceGuardrailResult:
    """Prevent non-grounded retrieval states from producing grounded claims."""

    knowledge_results = [
        result
        for result in tool_invocation_results
        if result.tool_name == "knowledge.search"
    ]
    if not knowledge_results:
        return EvidenceGuardrailResult(
            status=EvidenceGuardrailStatus.NOT_APPLICABLE,
            citations=list(citations),
            evidence=list(evidence),
        )

    has_usable_result = any(
        is_knowledge_result_usable(
            invocation_status=result.invocation_status,
            response_payload=result.response_payload,
        )
        for result in knowledge_results
    )
    grounded_claims = [item for item in evidence if _is_grounded_claim(item)]
    safe_evidence = [item for item in evidence if not _is_grounded_claim(item)]

    if not has_usable_result:
        if citations or grounded_claims:
            safe_evidence.append(
                "Retrieval was not grounded; citations and grounded claims were omitted."
            )
            return EvidenceGuardrailResult(
                status=EvidenceGuardrailStatus.DOWNGRADED,
                citations=[],
                evidence=safe_evidence,
                reason="retrieval_not_completed",
            )
        return EvidenceGuardrailResult(
            status=EvidenceGuardrailStatus.NO_GROUNDING,
            citations=[],
            evidence=safe_evidence,
            reason="retrieval_not_completed",
        )

    if not citations:
        if grounded_claims:
            safe_evidence.append(
                "Retrieval completed without valid citations; grounded claims were omitted."
            )
            return EvidenceGuardrailResult(
                status=EvidenceGuardrailStatus.DOWNGRADED,
                citations=[],
                evidence=safe_evidence,
                reason="valid_citations_missing",
            )
        return EvidenceGuardrailResult(
            status=EvidenceGuardrailStatus.NO_GROUNDING,
            citations=[],
            evidence=safe_evidence,
            reason="valid_citations_missing",
        )

    return EvidenceGuardrailResult(
        status=EvidenceGuardrailStatus.GROUNDED,
        citations=list(citations),
        evidence=list(evidence),
    )


def _is_grounded_claim(evidence_item: str) -> bool:
    lowered = evidence_item.lower()
    return "evidence grounded" in lowered or "rag-backed citations" in lowered
