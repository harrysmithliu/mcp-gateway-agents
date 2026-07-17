from __future__ import annotations

# The script supports direct execution from the repository root.
# ruff: noqa: E402

import argparse
import json
from pathlib import Path
import sys
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.verification.catalog import (
    PROFILES,
    STAGE_CATALOG,
    list_stage_names,
    resolve_stage_selection,
)
from backend.verification.contracts import (
    DeliveryVerificationReport,
    VerificationStageResult,
    VerificationStatus,
)
from backend.verification.runner import run_stage


StageRunner = Callable[..., VerificationStageResult]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run composable deterministic delivery verification stages."
    )
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILES),
        help="Run a named stage profile.",
    )
    parser.add_argument(
        "--stage",
        action="append",
        dest="stages",
        help="Run one stage and its dependencies; repeat for multiple stages.",
    )
    parser.add_argument(
        "--list-stages",
        action="store_true",
        help="Print the available stage metadata and exit.",
    )
    parser.add_argument(
        "--allow-paid-provider",
        action="store_true",
        help="Explicitly allow the paid Anthropic planner smoke stage.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    return parser


def build_stage_listing(allow_paid_provider: bool = False) -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "description": STAGE_CATALOG[name].description,
            "depends_on": list(STAGE_CATALOG[name].depends_on),
            "requires_runtime": STAGE_CATALOG[name].requires_runtime,
            "mutates_local_state": STAGE_CATALOG[name].mutates_local_state,
            "paid_provider": STAGE_CATALOG[name].paid_provider,
        }
        for name in list_stage_names(include_paid_provider=allow_paid_provider)
    ]


def execute_pipeline(
    selected_stages: tuple[str, ...],
    *,
    profile: str | None = None,
    project_root: Path = PROJECT_ROOT,
    timeout_seconds: float = 300.0,
    stage_runner: StageRunner = run_stage,
) -> DeliveryVerificationReport:
    results: list[VerificationStageResult] = []
    results_by_name: dict[str, VerificationStageResult] = {}
    for stage_name in selected_stages:
        stage = STAGE_CATALOG[stage_name]
        failed_dependencies = [
            dependency
            for dependency in stage.depends_on
            if results_by_name[dependency].status != VerificationStatus.PASSED
        ]
        if failed_dependencies:
            result = VerificationStageResult(
                stage=stage_name,
                status=VerificationStatus.BLOCKED,
                reason=f"dependency_failed:{','.join(failed_dependencies)}",
            )
        else:
            result = stage_runner(
                stage,
                project_root,
                timeout_seconds=timeout_seconds,
            )
        results.append(result)
        results_by_name[stage_name] = result

    overall_status = (
        VerificationStatus.PASSED
        if all(result.status == VerificationStatus.PASSED for result in results)
        else VerificationStatus.FAILED
    )
    return DeliveryVerificationReport(
        status=overall_status,
        profile=profile,
        selected_stages=selected_stages,
        stage_results=tuple(results),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_stages:
        print(
            json.dumps(
                {"stages": build_stage_listing(args.allow_paid_provider)},
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.profile is not None and args.stages:
        print(json.dumps({"status": "blocked", "reason": "profile_and_stage_are_mutually_exclusive"}))
        return 2
    try:
        selected_stages = resolve_stage_selection(
            tuple(args.stages or ()),
            profile=args.profile,
            allow_paid_provider=args.allow_paid_provider,
        )
    except ValueError as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}))
        return 2
    if not selected_stages:
        print(json.dumps({"status": "blocked", "reason": "no_verification_stage_selected"}))
        return 2

    report = execute_pipeline(
        selected_stages,
        profile=args.profile,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report.to_payload(), indent=2, sort_keys=True))
    return 0 if report.status == VerificationStatus.PASSED else 1


if __name__ == "__main__":
    raise SystemExit(main())
