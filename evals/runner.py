from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from evals.contracts import EvalCase, EvalObservation, EvalReport, EvalScore
from evals.loader import load_eval_cases
from evals.scoring import score_case
from evals.targets.base import EvaluationTarget


@dataclass(slots=True)
class EvaluationRunner:
    """Executes cases through a target and aggregates deterministic scores."""

    target: EvaluationTarget

    def run(
        self,
        cases: tuple[EvalCase, ...],
        dataset_name: str,
        dataset_version: str,
    ) -> EvalReport:
        scores = tuple(self._score_case(case) for case in cases)
        return EvalReport(
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            scores=scores,
            summary=build_summary(scores),
        )

    def run_dataset(
        self,
        dataset_path: str | Path,
        dataset_name: str,
        dataset_version: str,
    ) -> EvalReport:
        return self.run(
            cases=load_eval_cases(dataset_path),
            dataset_name=dataset_name,
            dataset_version=dataset_version,
        )

    def _score_case(self, case: EvalCase) -> EvalScore:
        try:
            observation = self.target.evaluate(case)
        except Exception as exc:
            observation = EvalObservation(
                case_id=case.case_id,
                error=type(exc).__name__,
            )
        if observation.case_id != case.case_id:
            observation = EvalObservation(
                case_id=case.case_id,
                error="case_id_mismatch",
            )
        return score_case(case, observation)


def build_summary(scores: tuple[EvalScore, ...]) -> dict[str, object]:
    total_cases = len(scores)
    passed_cases = sum(1 for score in scores if score.passed)
    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": total_cases - passed_cases,
        "pass_rate": passed_cases / total_cases if total_cases else 0.0,
        "all_hard_checks_passed": all(score.passed for score in scores),
        "average_tool_recall": _average(score.tool_recall for score in scores),
        "average_citation_coverage": _average(
            score.citation_coverage for score in scores
        ),
        "average_latency_ms": _average(score.latency_ms for score in scores),
    }


def write_report(report: EvalReport, output_path: str | Path) -> Path:
    """Write one stable, human-readable JSON report and return its path."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _average(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0
