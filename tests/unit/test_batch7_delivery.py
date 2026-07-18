from pathlib import Path
from types import SimpleNamespace

from backend.verification.contracts import VerificationStatus
from backend.verification.handoff import HandoffMode, HandoffRequest
from scripts.verify_batch7_delivery import execute_handoff


def local_delivery_payload() -> str:
    stages = [
        {"stage": stage, "status": "passed"}
        for stage in (
            "readiness",
            "data_state",
            "rag_mcp",
            "workflow",
            "cache_guardrails",
            "evaluation",
        )
    ]
    return '{"status": "passed", "stage_results": ' + str(stages).replace("'", '"') + "}"


def test_inspect_mode_runs_readiness_only() -> None:
    calls: list[list[str]] = []

    def runner(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout='{"status": "ready"}')

    report = execute_handoff(
        HandoffRequest(mode=HandoffMode.INSPECT),
        project_root=Path("/tmp/project"),
        python_executable="python-test",
        command_runner=runner,
    )

    assert report.status == VerificationStatus.PASSED
    assert calls[0][1].endswith("scripts/doctor_local_runtime.py")
    assert calls[0][-1] == "--require-frontend"
    assert report.evidence["readiness"] == "ready"


def test_verify_current_is_blocked_without_write_consent() -> None:
    report = execute_handoff(
        HandoffRequest(mode=HandoffMode.VERIFY_CURRENT),
        command_runner=lambda *_args, **_kwargs: None,
    )

    assert report.status == VerificationStatus.BLOCKED
    assert report.reason == "local_write_confirmation_required"


def test_verify_current_forwards_selected_profile() -> None:
    calls: list[list[str]] = []

    def runner(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=local_delivery_payload())

    report = execute_handoff(
        HandoffRequest(
            mode=HandoffMode.VERIFY_CURRENT,
            profile="local",
            allow_local_writes=True,
        ),
        project_root=Path("/tmp/project"),
        python_executable="python-test",
        command_runner=runner,
    )

    assert report.status == VerificationStatus.PASSED
    assert calls[0][-2:] == ["--profile", "local"]
    assert report.evidence["passed_stage_count"] == 6


def test_reset_and_verify_runs_confirmed_reset_before_delivery() -> None:
    calls: list[list[str]] = []

    def runner(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=local_delivery_payload())

    report = execute_handoff(
        HandoffRequest(
            mode=HandoffMode.RESET_AND_VERIFY,
            profile="local",
            allow_local_writes=True,
            confirm_reset=True,
        ),
        project_root=Path("/tmp/project"),
        python_executable="python-test",
        command_runner=runner,
    )

    assert report.status == VerificationStatus.PASSED
    assert calls[0][-3:] == ["--scope", "demo", "--confirm"]
    assert calls[1][-2:] == ["--profile", "local"]
    assert report.evidence["missing_stages"] == []


def test_verify_current_fails_when_delivery_stage_evidence_is_incomplete() -> None:
    def runner(_command, **_kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout='{"status": "passed", "stage_results": []}',
        )

    report = execute_handoff(
        HandoffRequest(
            mode=HandoffMode.VERIFY_CURRENT,
            allow_local_writes=True,
        ),
        command_runner=runner,
    )

    assert report.status == VerificationStatus.FAILED
    assert report.reason == "delivery_stage_evidence_incomplete"
