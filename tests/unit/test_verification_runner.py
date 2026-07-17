from pathlib import Path
from types import SimpleNamespace

from backend.verification.contracts import VerificationStage, VerificationStatus
from backend.verification.runner import parse_child_summary, run_stage


def test_child_json_summary_is_redacted_without_echoing_raw_payload() -> None:
    summary = parse_child_summary(
        '{"database_url":"postgresql://postgres:secret@db:5432/app",'
        '"access_token":"jwt-value","key_prefix":"agent:response"}'
    )

    assert summary["payload"] == {
        "database_url": "[redacted]",
        "access_token": "[redacted]",
        "key_prefix": "agent:response",
    }
    assert "secret" not in str(summary)
    assert "jwt-value" not in str(summary)


def test_non_json_summary_keeps_only_safe_metadata(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="plain output\n", stderr="secret")

    monkeypatch.setattr("backend.verification.runner.subprocess.run", fake_run)
    result = run_stage(
        VerificationStage(
            name="demo",
            description="Demo stage",
            script_path="scripts/demo.py",
        ),
        Path("/tmp/project"),
    )

    assert result.status == VerificationStatus.PASSED
    assert result.summary["format"] == "text"
    assert "plain output" not in str(result.summary)
    assert "secret" not in str(result.summary)


def test_nonzero_child_exit_becomes_failed_stage(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.verification.runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=3,
            stdout='{"status":"failed"}',
            stderr="failure details",
        ),
    )

    result = run_stage(
        VerificationStage(
            name="demo",
            description="Demo stage",
            script_path="scripts/demo.py",
        ),
        Path("/tmp/project"),
    )

    assert result.status == VerificationStatus.FAILED
    assert result.exit_code == 3
    assert result.reason == "stage_exit_nonzero"
