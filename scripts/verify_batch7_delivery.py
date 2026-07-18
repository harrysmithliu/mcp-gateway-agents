from __future__ import annotations

# The script supports direct execution from the repository root.
# ruff: noqa: E402

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.verification.handoff import (
    HandoffMode,
    HandoffReport,
    HandoffRequest,
    HandoffStepResult,
)
from backend.verification.contracts import VerificationStatus


REQUIRED_LOCAL_STAGES = (
    "readiness",
    "data_state",
    "rag_mcp",
    "workflow",
    "cache_guardrails",
    "evaluation",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Batch 7 delivery handoff checks."
    )
    parser.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in HandoffMode),
        default=HandoffMode.INSPECT.value,
    )
    parser.add_argument("--profile", default="local")
    parser.add_argument("--allow-local-writes", action="store_true")
    parser.add_argument("--confirm-reset", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    return parser


def _parse_summary(stdout: str) -> dict[str, object]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "format": "text",
            "line_count": len(stdout.splitlines()),
            "output_digest": hashlib.sha256(stdout.encode()).hexdigest(),
        }
    return {"format": "json", "payload": payload}


def _build_evidence(
    request: HandoffRequest,
    steps: list[HandoffStepResult],
) -> tuple[dict[str, object], str | None]:
    if not steps:
        return {}, "delivery_evidence_missing"
    payload = steps[-1].summary.get("payload")
    if not isinstance(payload, dict):
        return {}, "delivery_evidence_missing"
    if request.mode == HandoffMode.INSPECT:
        return {
            "readiness": payload.get("state", payload.get("status", "unknown"))
        }, None

    stage_results = payload.get("stage_results")
    if not isinstance(stage_results, list):
        return {}, "delivery_stage_evidence_missing"
    stage_statuses = {
        str(item["stage"]): str(item["status"])
        for item in stage_results
        if isinstance(item, dict) and "stage" in item and "status" in item
    }
    missing_stages = [
        stage for stage in REQUIRED_LOCAL_STAGES if stage not in stage_statuses
    ]
    evidence = {
        "stage_statuses": stage_statuses,
        "required_stage_count": len(REQUIRED_LOCAL_STAGES),
        "passed_stage_count": sum(
            status == VerificationStatus.PASSED.value
            for status in stage_statuses.values()
        ),
        "missing_stages": missing_stages,
    }
    if missing_stages:
        return evidence, "delivery_stage_evidence_incomplete"
    return evidence, None


def _build_commands(request: HandoffRequest) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if request.mode == HandoffMode.INSPECT:
        return (("scripts/doctor_local_runtime.py", ("--require-frontend",)),)
    if request.mode == HandoffMode.VERIFY_CURRENT:
        return (("scripts/verify_delivery.py", ("--profile", request.profile)),)
    if request.mode == HandoffMode.RESET_AND_VERIFY:
        return (
            (
                "scripts/reset_local_state.py",
                ("--scope", "demo", "--confirm"),
            ),
            (
                "scripts/verify_delivery.py",
                ("--profile", request.profile),
            ),
        )
    raise ValueError(f"unsupported_handoff_mode:{request.mode.value}")


def execute_handoff(
    request: HandoffRequest,
    *,
    project_root: Path = PROJECT_ROOT,
    python_executable: str | None = None,
    timeout_seconds: float = 300.0,
    command_runner: Any = subprocess.run,
) -> HandoffReport:
    validation_status, validation_reason = request.validation()
    if validation_status != VerificationStatus.PASSED:
        return HandoffReport(
            request=request,
            status=validation_status,
            reason=validation_reason,
        )

    try:
        commands = _build_commands(request)
    except ValueError as exc:
        return HandoffReport(
            request=request,
            status=VerificationStatus.BLOCKED,
            reason=str(exc),
        )

    steps: list[HandoffStepResult] = []
    for script_path, arguments in commands:
        command = [
            python_executable or sys.executable,
            str(project_root / script_path),
            *arguments,
        ]
        try:
            completed = command_runner(
                command,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            steps.append(
                HandoffStepResult(
                    name=script_path,
                    status=VerificationStatus.FAILED,
                    reason="handoff_step_timeout",
                )
            )
            break
        except OSError as exc:
            steps.append(
                HandoffStepResult(
                    name=script_path,
                    status=VerificationStatus.FAILED,
                    reason=f"handoff_step_process_error:{type(exc).__name__}",
                )
            )
            break

        step_status = (
            VerificationStatus.PASSED
            if completed.returncode == 0
            else VerificationStatus.FAILED
        )
        steps.append(
            HandoffStepResult(
                name=script_path,
                status=step_status,
                exit_code=completed.returncode,
                summary=_parse_summary(completed.stdout),
                reason=(
                    None
                    if step_status == VerificationStatus.PASSED
                    else "handoff_step_failed"
                ),
            )
        )
        if step_status != VerificationStatus.PASSED:
            break

    evidence, evidence_reason = _build_evidence(request, steps)
    overall_status = (
        VerificationStatus.PASSED
        if (
            steps
            and all(step.status == VerificationStatus.PASSED for step in steps)
            and evidence_reason is None
        )
        else VerificationStatus.FAILED
    )
    return HandoffReport(
        request=request,
        status=overall_status,
        steps=tuple(steps),
        evidence=evidence,
        reason=(
            None
            if overall_status == VerificationStatus.PASSED
            else evidence_reason or steps[-1].reason
        ),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = execute_handoff(
        HandoffRequest(
            mode=HandoffMode(args.mode),
            profile=args.profile,
            allow_local_writes=args.allow_local_writes,
            confirm_reset=args.confirm_reset,
        ),
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report.to_payload(), indent=2, sort_keys=True))
    return 0 if report.status == VerificationStatus.PASSED else 1


if __name__ == "__main__":
    raise SystemExit(main())
