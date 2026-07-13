from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib import error, request
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.bootstrap import apply_local_sql_plan, build_local_sql_plan
from backend.storage.models import RiskAlertRecord
from backend.storage.runtime import build_storage_bundle
from backend.storage.settings import get_settings


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8000")
DEMO_PASSWORD = "demo-password"


def api_request(
    method: str,
    endpoint_path: str,
    payload: dict[str, object] | None = None,
    access_token: str | None = None,
) -> tuple[int, dict[str, object]]:
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    api_request = request.Request(
        url=f"{API_BASE_URL.rstrip('/')}/{endpoint_path.lstrip('/')}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with request.urlopen(api_request, timeout=10.0) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        return exc.code, json.loads(response_body) if response_body else {}
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach the API at {API_BASE_URL}.") from exc


def login(username: str) -> tuple[str, list[str]]:
    status_code, payload = api_request(
        "POST",
        "/auth/login",
        {"username": username, "password": DEMO_PASSWORD},
    )
    if status_code != 200:
        raise RuntimeError(f"Login failed for {username}: HTTP {status_code}.")
    return str(payload["access_token"]), list(payload["user"].get("roles", []))


def expect_status(actual_status: int, expected_status: int, operation: str) -> None:
    if actual_status != expected_status:
        raise RuntimeError(
            f"{operation} returned HTTP {actual_status}, expected {expected_status}."
        )


def create_verification_alert() -> str:
    settings = get_settings()
    storage_bundle = build_storage_bundle(settings)
    alert_id = str(uuid4())
    storage_bundle.risk_alert_repository.create_risk_alert(
        RiskAlertRecord(
            alert_id=alert_id,
            alert_type="round7_verification",
            severity="medium",
            status="open",
            summary="Round 7 approval workflow verification alert.",
            details={"source": "verify_round7_workflow.py"},
            actor_user_id=2,
        )
    )
    return alert_id


def main() -> int:
    settings = get_settings()
    sql_plan = build_local_sql_plan(PROJECT_ROOT)
    apply_local_sql_plan(build_storage_bundle(settings).database_client, sql_plan)

    analyst_token, analyst_roles = login("analyst_demo")
    risk_token, risk_roles = login("risk_operator_demo")
    supervisor_token, supervisor_roles = login("supervisor_demo")

    status_code, _ = api_request(
        "POST",
        "/accounts/search",
        {"query": "high risk", "limit": 3},
        analyst_token,
    )
    expect_status(status_code, 200, "analyst account search")
    status_code, _ = api_request(
        "GET",
        "/audit/recent-events?limit=5",
        access_token=analyst_token,
    )
    expect_status(status_code, 403, "analyst audit access")

    status_code, score_payload = api_request(
        "POST",
        "/risk/batch-score",
        {"account_ids": ["acct-atlas-01", "acct-beacon-17"]},
        risk_token,
    )
    expect_status(status_code, 200, "risk batch scoring")

    alert_id = create_verification_alert()
    status_code, status_payload = api_request(
        "POST",
        f"/ops/alerts/{alert_id}/status",
        {"status": "acknowledged"},
        risk_token,
    )
    expect_status(status_code, 200, "risk operator alert acknowledgement")

    status_code, request_payload = api_request(
        "POST",
        f"/ops/alerts/{alert_id}/approval",
        {"reason": "Supervisor review required for the sensitive follow-up."},
        risk_token,
    )
    expect_status(status_code, 200, "approval request")
    approval_id = str(request_payload["approval_id"])

    status_code, approvals_payload = api_request(
        "GET",
        "/ops/approvals?limit=20",
        access_token=supervisor_token,
    )
    expect_status(status_code, 200, "supervisor approval queue")
    if not any(
        str(item.get("approval_id")) == approval_id
        for item in approvals_payload["approvals"]
    ):
        raise RuntimeError("Supervisor approval queue did not contain the requested approval.")

    status_code, decision_payload = api_request(
        "POST",
        f"/ops/approvals/{approval_id}/decision",
        {"decision": "approved", "reason": "Evidence and operational context reviewed."},
        supervisor_token,
    )
    expect_status(status_code, 200, "supervisor approval decision")
    if decision_payload.get("approval_status") != "approved":
        raise RuntimeError("Supervisor approval decision did not complete.")

    status_code, audit_payload = api_request(
        "GET",
        "/audit/recent-events?limit=20",
        access_token=supervisor_token,
    )
    expect_status(status_code, 200, "supervisor audit review")

    status_code, _ = api_request(
        "GET",
        "/ops/approvals?limit=5",
        access_token=analyst_token,
    )
    expect_status(status_code, 403, "analyst approval access")

    print(
        json.dumps(
            {
                "api_base_url": API_BASE_URL,
                "analyst_roles": analyst_roles,
                "risk_operator_roles": risk_roles,
                "supervisor_roles": supervisor_roles,
                "scored_accounts": score_payload.get("total_scored", 0),
                "alert_status": status_payload.get("status"),
                "approval_status": decision_payload.get("approval_status"),
                "audit_event_count": len(audit_payload.get("events", [])),
                "authorization_checks": "passed",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
