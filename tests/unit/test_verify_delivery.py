from pathlib import Path

from backend.verification.contracts import VerificationStageResult, VerificationStatus
from scripts.verify_delivery import (
    build_stage_listing,
    execute_pipeline,
    main,
)


def test_pipeline_blocks_dependents_but_runs_independent_stages() -> None:
    calls: list[str] = []

    def fake_runner(stage, project_root: Path, **kwargs):
        calls.append(stage.name)
        status = (
            VerificationStatus.FAILED
            if stage.name == "data_state"
            else VerificationStatus.PASSED
        )
        return VerificationStageResult(stage=stage.name, status=status, exit_code=0)

    report = execute_pipeline(
        ("readiness", "data_state", "rag_mcp", "cache_guardrails"),
        stage_runner=fake_runner,
    )

    assert report.status == VerificationStatus.FAILED
    assert calls == ["readiness", "data_state", "cache_guardrails"]
    results = {result.stage: result for result in report.stage_results}
    assert results["rag_mcp"].status == VerificationStatus.BLOCKED
    assert results["rag_mcp"].reason == "dependency_failed:data_state"


def test_stage_listing_hides_paid_stage_by_default() -> None:
    default_names = {item["name"] for item in build_stage_listing()}
    paid_names = {
        item["name"] for item in build_stage_listing(allow_paid_provider=True)
    }

    assert "anthropic_planner" not in default_names
    assert "anthropic_planner" in paid_names


def test_cli_rejects_empty_selection_and_profile_stage_mix(capsys) -> None:
    assert main([]) == 2
    assert "no_verification_stage_selected" in capsys.readouterr().out

    assert main(["--profile", "offline", "--stage", "evaluation"]) == 2
    assert "mutually_exclusive" in capsys.readouterr().out
