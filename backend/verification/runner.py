from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

from backend.verification.contracts import (
    VerificationStage,
    VerificationStageResult,
    VerificationStatus,
)


SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "database_url",
    "password",
    "redis_url",
    "secret",
    "token",
}


def _redact_string(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme and parsed.hostname and parsed.password is not None:
        host = parsed.hostname
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        return f"{parsed.scheme}://{host}{parsed.path or '/'}"
    return value


def redact_summary(value: Any, key: str | None = None) -> Any:
    """Keep child summaries useful while excluding credentials and raw payloads."""

    if key is not None and key.lower() in SENSITIVE_KEYS:
        return "[redacted]"
    if isinstance(value, dict):
        return {
            str(item_key): redact_summary(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [redact_summary(item) for item in value]
    if isinstance(value, tuple):
        return [redact_summary(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def parse_child_summary(stdout: str) -> dict[str, object]:
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "format": "text",
            "line_count": len(stdout.splitlines()),
            "output_digest": hashlib.sha256(stdout.encode()).hexdigest(),
        }
    if not isinstance(parsed, dict):
        return {
            "format": "json",
            "value_type": type(parsed).__name__,
        }
    return {
        "format": "json",
        "payload": redact_summary(parsed),
    }


def run_stage(
    stage: VerificationStage,
    project_root: Path,
    *,
    python_executable: str | None = None,
    timeout_seconds: float = 300.0,
) -> VerificationStageResult:
    command = [
        python_executable or sys.executable,
        str(project_root / stage.script_path),
        *stage.arguments,
    ]
    started_at = perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return VerificationStageResult(
            stage=stage.name,
            status=VerificationStatus.FAILED,
            duration_ms=_duration_ms(started_at),
            reason="stage_timeout",
        )
    except OSError as exc:
        return VerificationStageResult(
            stage=stage.name,
            status=VerificationStatus.FAILED,
            duration_ms=_duration_ms(started_at),
            reason=f"stage_process_error:{type(exc).__name__}",
        )

    return VerificationStageResult(
        stage=stage.name,
        status=(
            VerificationStatus.PASSED
            if completed.returncode == 0
            else VerificationStatus.FAILED
        ),
        exit_code=completed.returncode,
        duration_ms=_duration_ms(started_at),
        summary=parse_child_summary(completed.stdout),
        reason=(None if completed.returncode == 0 else "stage_exit_nonzero"),
    )


def _duration_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)
