from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class ReadinessState(StrEnum):
    """Stable states shared by component and overall readiness reports."""

    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class ReadinessReason(StrEnum):
    """Non-secret reason codes that can guide local remediation."""

    CONFIGURED = "configured"
    CONFIGURATION_MISSING = "configuration_missing"
    DISABLED_BY_CONFIGURATION = "disabled_by_configuration"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    DEPENDENCY_TIMEOUT = "dependency_timeout"
    INITIALIZATION_FAILED = "initialization_failed"
    UNSUPPORTED_MODE = "unsupported_mode"


@dataclass(frozen=True, slots=True)
class ReadinessComponent:
    """Redacted status for one runtime component."""

    name: str
    state: ReadinessState
    reason_code: ReadinessReason
    message: str
    remediation: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "state": self.state.value,
            "reason_code": self.reason_code.value,
            "message": self.message,
            "remediation": self.remediation,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class RuntimeReadinessReport:
    """Stable, JSON-ready report for the local runtime doctor."""

    state: ReadinessState
    components: tuple[ReadinessComponent, ...]
    config: Mapping[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "components": [component.to_payload() for component in self.components],
            "config": dict(self.config),
        }
