from evals.contracts import EvalCase, EvalObservation
from evals.scoring import score_case


def build_case(**overrides: object) -> EvalCase:
    values: dict[str, object] = {
        "case_id": "policy-case",
        "role": "analyst",
        "message_text": "Find policy evidence.",
        "required_tools": ("knowledge.search",),
        "forbidden_tools": ("ops.create_alert_or_action",),
        "expected_citation_chunk_ids": ("chunk-1",),
        "requires_rag": True,
        "expected_retrieval_status": "completed",
        "expected_authorization_scope": ("internal",),
    }
    values.update(overrides)
    return EvalCase(**values)


def test_score_case_passes_complete_grounded_observation() -> None:
    score = score_case(
        build_case(),
        EvalObservation(
            case_id="policy-case",
            tool_names=("knowledge.search",),
            invocation_statuses=("completed",),
            citation_chunk_ids=("chunk-1",),
            retrieval_status="completed",
            authorization_scope=("internal",),
        ),
    )

    assert score.passed is True
    assert score.tool_recall == 1.0
    assert score.citation_coverage == 1.0
    assert all(score.checks.values())


def test_score_case_fails_forbidden_tool_and_missing_citation() -> None:
    score = score_case(
        build_case(),
        EvalObservation(
            case_id="policy-case",
            tool_names=("knowledge.search", "ops.create_alert_or_action"),
            invocation_statuses=("completed", "completed"),
            citation_chunk_ids=(),
            retrieval_status="completed",
            authorization_scope=("internal",),
        ),
    )

    assert score.passed is False
    assert score.checks["forbidden_tools"] is False
    assert score.checks["citation_coverage"] is False
