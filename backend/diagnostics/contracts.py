from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from collections.abc import Mapping
from datetime import datetime
from typing import Any


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


_SENSITIVE_FIELD_MARKERS = (
    "access_key",
    "api_key",
    "authorization",
    "connection_string",
    "credential",
    "password",
    "secret",
    "token",
    "url",
)


def _is_sensitive_field(field_name: str) -> bool:
    normalized_name = field_name.lower()
    return any(marker in normalized_name for marker in _SENSITIVE_FIELD_MARKERS)


def _redact_status_value(value: Any) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _redact_status_value(item)
            for key, item in value.items()
            if not _is_sensitive_field(str(key))
        }
    if isinstance(value, (list, tuple)):
        return [_redact_status_value(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class AdminRuntimeStatusReport:
    """Read-only, redacted operational status projection for administrators."""

    observed_at: datetime
    environment: str
    readiness: RuntimeReadinessReport
    runtime_mode: Mapping[str, object] = field(default_factory=dict)
    migration: Mapping[str, object] = field(default_factory=dict)
    mcp: Mapping[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "observed_at": self.observed_at.isoformat(),
            "environment": self.environment,
            "readiness": _redact_status_value(self.readiness.to_payload()),
            "runtime_mode": _redact_status_value(self.runtime_mode),
            "migration": _redact_status_value(self.migration),
            "mcp": _redact_status_value(self.mcp),
        }
