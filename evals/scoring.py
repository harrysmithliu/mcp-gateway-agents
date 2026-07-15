from __future__ import annotations

from evals.contracts import EvalCase, EvalObservation, EvalScore


def score_case(case: EvalCase, observation: EvalObservation) -> EvalScore:
    """Score one observation using deterministic, provider-neutral checks."""

    actual_tools = set(observation.tool_names)
    required_tools = set(case.required_tools)
    forbidden_tools = set(case.forbidden_tools)
    required_tools_passed = required_tools.issubset(actual_tools)
    forbidden_tools_passed = not forbidden_tools.intersection(actual_tools)

    invocation_status_passed = True
    if case.required_tools or case.expected_invocation_status != "completed":
        invocation_status_passed = bool(observation.invocation_statuses) and all(
            status == case.expected_invocation_status
            for status in observation.invocation_statuses
        )

    retrieval_status_passed = True
    if case.expected_retrieval_status is not None:
        retrieval_status_passed = (
            observation.retrieval_status == case.expected_retrieval_status
        )

    authorization_scope_passed = True
    if case.expected_authorization_scope:
        authorization_scope_passed = (
            observation.authorization_scope == case.expected_authorization_scope
        )

    expected_citations = set(case.expected_citation_chunk_ids)
    observed_citations = set(observation.citation_chunk_ids)
    citation_coverage = _coverage(expected_citations, observed_citations)
    citation_passed = (
        citation_coverage == 1.0 if case.requires_rag else observation.citation_schema_valid
    )
    checks = {
        "required_tools": required_tools_passed,
        "forbidden_tools": forbidden_tools_passed,
        "invocation_status": invocation_status_passed,
        "retrieval_status": retrieval_status_passed,
        "authorization_scope": authorization_scope_passed,
        "citation_schema": observation.citation_schema_valid,
        "citation_coverage": citation_passed,
        "no_target_error": observation.error is None,
    }
    return EvalScore(
        case_id=case.case_id,
        passed=all(checks.values()),
        checks=checks,
        tool_recall=_coverage(required_tools, actual_tools),
        citation_coverage=citation_coverage,
        latency_ms=observation.latency_ms,
        error=observation.error,
    )


def _coverage(expected: set[str], actual: set[str]) -> float:
    if not expected:
        return 1.0
    return len(expected.intersection(actual)) / len(expected)
