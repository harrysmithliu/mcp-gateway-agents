from backend.guardrails.output import (
    EvidenceGuardrailStatus,
    validate_evidence_bound_output,
)
from backend.mcp_gateway.models import ToolInvocationResult


def knowledge_result(
    status: str,
    citations: list[dict[str, object]] | None = None,
) -> ToolInvocationResult:
    return ToolInvocationResult(
        tool_name="knowledge.search",
        domain="knowledge",
        invocation_status="completed",
        response_payload={
            "result_status": status,
            "retrieval_metadata": {"status": status},
            "citations": citations or [],
        },
    )


def test_failed_retrieval_downgrades_citations_and_grounded_claims() -> None:
    result = validate_evidence_bound_output(
        tool_invocation_results=[
            knowledge_result(
                "failed",
                citations=[{"document_id": "doc-1", "title": "Invalid source"}],
            )
        ],
        citations=[{"document_id": "doc-1", "title": "Invalid source"}],
        evidence=["Evidence grounded by 1 knowledge citation(s)."],
    )

    assert result.status is EvidenceGuardrailStatus.DOWNGRADED
    assert result.reason == "retrieval_not_completed"
    assert result.citations == []
    assert result.evidence == [
        "Retrieval was not grounded; citations and grounded claims were omitted."
    ]


def test_completed_retrieval_with_citations_is_grounded() -> None:
    citations = [{"document_id": "doc-1", "title": "Trading Policy"}]
    result = validate_evidence_bound_output(
        tool_invocation_results=[knowledge_result("completed", citations)],
        citations=citations,
        evidence=["Evidence grounded by 1 knowledge citation(s)."],
    )

    assert result.status is EvidenceGuardrailStatus.GROUNDED
    assert result.reason is None
    assert result.citations == citations
    assert result.evidence == ["Evidence grounded by 1 knowledge citation(s)."]


def test_non_knowledge_workflow_is_not_subject_to_evidence_guardrail() -> None:
    result = validate_evidence_bound_output(
        tool_invocation_results=[],
        citations=[],
        evidence=["Trade metrics completed."],
    )

    assert result.status is EvidenceGuardrailStatus.NOT_APPLICABLE
    assert result.reason is None
    assert result.evidence == ["Trade metrics completed."]
