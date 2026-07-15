from pathlib import Path

from evals.contracts import EvalCase, EvalObservation
from evals.runner import EvaluationRunner, build_summary, write_report


class FakeEvaluationTarget:
    def __init__(self, observations: dict[str, EvalObservation]) -> None:
        self.observations = observations

    def evaluate(self, case: EvalCase) -> EvalObservation:
        return self.observations[case.case_id]


def build_case(case_id: str) -> EvalCase:
    return EvalCase(
        case_id=case_id,
        role="analyst",
        message_text="Find policy evidence.",
        required_tools=("knowledge.search",),
        expected_citation_chunk_ids=("chunk-1",),
        requires_rag=True,
        expected_retrieval_status="completed",
        expected_authorization_scope=("internal",),
    )


def build_observation(case_id: str) -> EvalObservation:
    return EvalObservation(
        case_id=case_id,
        tool_names=("knowledge.search",),
        invocation_statuses=("completed",),
        citation_chunk_ids=("chunk-1",),
        retrieval_status="completed",
        authorization_scope=("internal",),
        latency_ms=12,
    )


def test_runner_aggregates_scores_and_writes_json_report(tmp_path: Path) -> None:
    cases = (build_case("case-1"), build_case("case-2"))
    target = FakeEvaluationTarget(
        observations={case.case_id: build_observation(case.case_id) for case in cases}
    )

    report = EvaluationRunner(target=target).run(
        cases=cases,
        dataset_name="core",
        dataset_version="v1",
    )
    output_path = write_report(report, tmp_path / "evaluations" / "core.json")

    assert report.summary == {
        "total_cases": 2,
        "passed_cases": 2,
        "failed_cases": 0,
        "pass_rate": 1.0,
        "all_hard_checks_passed": True,
        "average_tool_recall": 1.0,
        "average_citation_coverage": 1.0,
        "average_latency_ms": 12.0,
    }
    assert output_path.exists()
    assert '"dataset_version": "v1"' in output_path.read_text(encoding="utf-8")


def test_summary_reports_failure_without_hiding_case_failures() -> None:
    report_summary = build_summary(
        (
            type(
                "Score",
                (),
                {
                    "passed": True,
                    "tool_recall": 1.0,
                    "citation_coverage": 1.0,
                    "latency_ms": 10,
                },
            )(),
            type(
                "Score",
                (),
                {
                    "passed": False,
                    "tool_recall": 0.5,
                    "citation_coverage": 0.0,
                    "latency_ms": 30,
                },
            )(),
        )
    )

    assert report_summary["passed_cases"] == 1
    assert report_summary["failed_cases"] == 1
    assert report_summary["pass_rate"] == 0.5
    assert report_summary["all_hard_checks_passed"] is False
