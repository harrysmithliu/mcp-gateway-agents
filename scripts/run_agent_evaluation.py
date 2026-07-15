from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app
from evals.loader import load_eval_cases
from evals.runner import EvaluationRunner, write_report
from evals.targets.in_process import InProcessEvaluationTarget


DEFAULT_DATASET = PROJECT_ROOT / "evals" / "datasets" / "core_v1.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts" / "evaluations" / "core_v1.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the offline deterministic Agent evaluation dataset."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target = InProcessEvaluationTarget(
        retrieval_service=app.state.container.retrieval_service,
    )
    cases = load_eval_cases(args.dataset)
    report = EvaluationRunner(target=target).run(
        cases=cases,
        dataset_name=args.dataset.stem,
        dataset_version="v1",
    )
    output_path = write_report(report, args.output)
    summary = report.summary
    print(
        f"evaluation={report.dataset_name} cases={summary['total_cases']} "
        f"passed={summary['passed_cases']} failed={summary['failed_cases']} "
        f"pass_rate={summary['pass_rate']:.3f} report={output_path}"
    )
    return 0 if summary["all_hard_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
