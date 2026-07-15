from pathlib import Path

import pytest

from evals.contracts import EvalCase, EvalReport, EvalScore
from evals.loader import load_eval_cases


DATASET_PATH = Path(__file__).resolve().parents[2] / "evals" / "datasets" / "core_v1.jsonl"


def test_core_dataset_loads_unique_cases_and_expected_coverage() -> None:
    cases = load_eval_cases(DATASET_PATH)

    assert len(cases) == 10
    assert len({case.case_id for case in cases}) == 10
    assert {case.role for case in cases} == {"analyst", "risk_operator", "admin"}
    assert any(case.requires_rag for case in cases)
    assert any(case.runtime_profile == "retrieval_disabled" for case in cases)


def test_eval_case_rejects_overlapping_tool_expectations() -> None:
    with pytest.raises(ValueError, match="both required and forbidden"):
        EvalCase(
            case_id="invalid-overlap",
            role="analyst",
            message_text="Test overlap.",
            required_tools=("knowledge.search",),
            forbidden_tools=("knowledge.search",),
        )


def test_eval_case_requires_expected_citations_for_rag_cases() -> None:
    with pytest.raises(ValueError, match="citation chunk ids"):
        EvalCase(
            case_id="invalid-rag-case",
            role="analyst",
            message_text="Test missing citations.",
            requires_rag=True,
        )


def test_eval_report_serializes_scores_without_runtime_objects() -> None:
    report = EvalReport(
        dataset_name="core",
        dataset_version="v1",
        scores=(
            EvalScore(
                case_id="case-1",
                passed=True,
                checks={"required_tools": True},
                tool_recall=1.0,
            ),
        ),
        summary={"pass_rate": 1.0},
    )

    assert report.to_payload() == {
        "dataset_name": "core",
        "dataset_version": "v1",
        "scores": [
            {
                "case_id": "case-1",
                "passed": True,
                "checks": {"required_tools": True},
                "tool_recall": 1.0,
                "citation_coverage": 0.0,
                "latency_ms": 0,
                "error": None,
            }
        ],
        "summary": {"pass_rate": 1.0},
    }
