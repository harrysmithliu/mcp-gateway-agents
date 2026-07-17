from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class VerificationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class VerificationStage:
    """Metadata for one existing verifier exposed through the pipeline."""

    name: str
    description: str
    script_path: str
    arguments: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    requires_runtime: bool = False
    mutates_local_state: bool = False
    paid_provider: bool = False


@dataclass(frozen=True, slots=True)
class VerificationStageResult:
    stage: str
    status: VerificationStatus
    exit_code: int | None = None
    duration_ms: int = 0
    summary: Mapping[str, object] = field(default_factory=dict)
    reason: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "summary": dict(self.summary),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class DeliveryVerificationReport:
    status: VerificationStatus
    selected_stages: tuple[str, ...]
    stage_results: tuple[VerificationStageResult, ...]
    profile: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "profile": self.profile,
            "selected_stages": list(self.selected_stages),
            "stage_results": [
                result.to_payload() for result in self.stage_results
            ],
        }
