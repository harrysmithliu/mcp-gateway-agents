from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping

from backend.verification.contracts import VerificationStatus


class HandoffMode(StrEnum):
    """Supported delivery handoff execution modes."""

    INSPECT = "inspect"
    VERIFY_CURRENT = "verify_current"
    RESET_AND_VERIFY = "reset_and_verify"


@dataclass(frozen=True, slots=True)
class HandoffRequest:
    """Validated intent for a delivery handoff run."""

    mode: HandoffMode
    profile: str = "local"
    allow_local_writes: bool = False
    confirm_reset: bool = False

    def validation(self) -> tuple[VerificationStatus, str | None]:
        if self.mode == HandoffMode.INSPECT:
            return VerificationStatus.PASSED, None
        if not self.allow_local_writes:
            return (
                VerificationStatus.BLOCKED,
                "local_write_confirmation_required",
            )
        if self.mode == HandoffMode.RESET_AND_VERIFY and not self.confirm_reset:
            return VerificationStatus.BLOCKED, "reset_confirmation_required"
        return VerificationStatus.PASSED, None

    def to_payload(self) -> dict[str, object]:
        status, reason = self.validation()
        return {
            "mode": self.mode.value,
            "profile": self.profile,
            "allow_local_writes": self.allow_local_writes,
            "confirm_reset": self.confirm_reset,
            "status": status.value,
            "reason": reason,
        }


@dataclass(frozen=True, slots=True)
class HandoffStepResult:
    name: str
    status: VerificationStatus
    exit_code: int | None = None
    summary: Mapping[str, object] = field(default_factory=dict)
    reason: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "summary": dict(self.summary),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class HandoffReport:
    request: HandoffRequest
    status: VerificationStatus
    steps: tuple[HandoffStepResult, ...] = ()
    evidence: Mapping[str, object] = field(default_factory=dict)
    reason: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "request": self.request.to_payload(),
            "status": self.status.value,
            "steps": [step.to_payload() for step in self.steps],
            "evidence": dict(self.evidence),
            "reason": self.reason,
        }
