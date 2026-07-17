from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.smoke.http_helpers import assert_success, build_demo_client


def test_supervisor_can_review_approvals_and_audit() -> None:
    client = build_demo_client("supervisor_demo")

    approvals_payload = assert_success(client.get("/ops/approvals?limit=5"))
    assert approvals_payload["limit"] == 5
    assert approvals_payload["query_status"] in {"completed", "degraded"}
    assert isinstance(approvals_payload["approvals"], list)

    audit_payload = assert_success(client.get("/audit/recent-events?limit=5"))
    assert audit_payload["limit"] == 5
    assert audit_payload["query_status"] in {"completed", "degraded"}
    assert isinstance(audit_payload["events"], list)

    tool_payload = assert_success(client.get("/audit/tool-invocations?limit=5"))
    assert tool_payload["limit"] == 5
    assert tool_payload["query_status"] in {"completed", "degraded"}
    assert isinstance(tool_payload["tool_calls"], list)


def test_supervisor_decision_preserves_unknown_approval_contract() -> None:
    client = build_demo_client("supervisor_demo")

    payload = assert_success(
        client.post(
            "/ops/approvals/00000000-0000-0000-0000-000000000000/decision",
            json={
                "decision": "approved",
                "reason": "Round 4 public contract check.",
            },
        )
    )

    assert payload["approval_status"] in {"not_found", "failed"}


def test_analyst_cannot_review_approvals_or_audit() -> None:
    client = build_demo_client("analyst_demo")

    approvals_response = client.get("/ops/approvals?limit=5")
    audit_response = client.get("/audit/recent-events?limit=5")

    assert approvals_response.status_code == 403
    assert audit_response.status_code == 403
