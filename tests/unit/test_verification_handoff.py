from backend.verification.contracts import VerificationStatus
from backend.verification.handoff import HandoffMode, HandoffRequest


def test_inspect_mode_is_read_only_by_contract() -> None:
    request = HandoffRequest(mode=HandoffMode.INSPECT)

    assert request.validation() == (VerificationStatus.PASSED, None)
    assert request.to_payload()["allow_local_writes"] is False


def test_verify_current_requires_explicit_local_write_consent() -> None:
    request = HandoffRequest(mode=HandoffMode.VERIFY_CURRENT)

    assert request.validation() == (
        VerificationStatus.BLOCKED,
        "local_write_confirmation_required",
    )


def test_reset_and_verify_requires_explicit_reset_confirmation() -> None:
    request = HandoffRequest(
        mode=HandoffMode.RESET_AND_VERIFY,
        allow_local_writes=True,
    )

    assert request.validation() == (
        VerificationStatus.BLOCKED,
        "reset_confirmation_required",
    )
