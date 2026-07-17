from __future__ import annotations

import argparse
import json
from urllib import request
from urllib.parse import urlparse


def _component(
    name: str,
    state: str,
    reason_code: str,
    message: str,
    remediation: str | None = None,
) -> dict[str, object]:
    return {
        "name": name,
        "state": state,
        "reason_code": reason_code,
        "message": message,
        "remediation": remediation,
        "details": {},
    }


def fetch_json(url: str, timeout_seconds: float) -> dict[str, object]:
    with request.urlopen(url, timeout=timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Endpoint returned a non-object JSON payload.")
    return payload


def check_http_reachable(url: str, timeout_seconds: float) -> None:
    with request.urlopen(url, timeout=timeout_seconds) as response:
        if response.status < 200 or response.status >= 400:
            raise OSError(f"Unexpected HTTP status: {response.status}")


def redact_target(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or "unknown"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    path = parsed.path or "/"
    return f"{parsed.scheme or 'http'}://{host}{path}"


def build_doctor_report(
    api_base_url: str,
    frontend_url: str,
    timeout_seconds: float = 5.0,
    require_frontend: bool = False,
) -> dict[str, object]:
    api_url = f"{api_base_url.rstrip('/')}/health"
    try:
        health_payload = fetch_json(api_url, timeout_seconds)
        readiness = health_payload.get("readiness")
        if not isinstance(readiness, dict):
            raise ValueError("Backend health payload has no readiness report.")
        backend_components = readiness.get("components", [])
        if not isinstance(backend_components, list):
            raise ValueError("Backend readiness components are not a list.")
        backend_state = str(readiness.get("state", "unavailable"))
        backend_error = None
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        backend_state = "unavailable"
        backend_components = [
            _component(
                "backend",
                "unavailable",
                "dependency_unavailable",
                "The backend health endpoint could not be read.",
                "Start the backend service and verify the API base URL.",
            )
        ]
        readiness = {"state": backend_state, "components": backend_components, "config": {}}
        backend_error = type(exc).__name__

    try:
        check_http_reachable(frontend_url.rstrip("/") + "/", timeout_seconds)
        frontend = _component(
            "frontend",
            "ready",
            "configured",
            "Frontend endpoint responded to a read-only request.",
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        frontend = _component(
            "frontend",
            "unavailable",
            "dependency_unavailable",
            "The frontend endpoint could not be reached.",
            "Start the frontend service and verify the frontend URL.",
        )

    components = [*backend_components, frontend]
    overall_state = backend_state
    if require_frontend and frontend["state"] == "unavailable":
        overall_state = "unavailable"
    elif overall_state == "ready" and frontend["state"] == "unavailable":
        overall_state = "degraded"

    report: dict[str, object] = {
        "state": overall_state,
        "components": components,
        "config": dict(readiness.get("config", {})),
        "targets": {
            "backend_health": redact_target(api_url),
            "frontend": redact_target(frontend_url.rstrip("/") + "/"),
        },
    }
    if backend_error is not None:
        report["backend_error_type"] = backend_error
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run read-only local backend and frontend readiness checks."
    )
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:8501")
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument(
        "--require-frontend",
        action="store_true",
        help="Treat frontend reachability as required instead of degraded.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_doctor_report(
        api_base_url=args.api_base_url,
        frontend_url=args.frontend_url,
        timeout_seconds=args.timeout_seconds,
        require_frontend=args.require_frontend,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["state"] in {"ready", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
