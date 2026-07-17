from backend.verification.contracts import (
    DeliveryVerificationReport,
    VerificationStageResult,
    VerificationStatus,
)


def test_verification_report_serializes_stable_stage_results() -> None:
    report = DeliveryVerificationReport(
        status=VerificationStatus.PASSED,
        profile="offline",
        selected_stages=("cache_guardrails", "evaluation"),
        stage_results=(
            VerificationStageResult(
                stage="evaluation",
                status=VerificationStatus.PASSED,
                exit_code=0,
                duration_ms=12,
                summary={"passed_cases": 8},
            ),
        ),
    )

    assert report.to_payload() == {
        "status": "passed",
        "profile": "offline",
        "selected_stages": ["cache_guardrails", "evaluation"],
        "stage_results": [
            {
                "stage": "evaluation",
                "status": "passed",
                "exit_code": 0,
                "duration_ms": 12,
                "summary": {"passed_cases": 8},
                "reason": None,
            }
        ],
    }
