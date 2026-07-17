from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.smoke.http_helpers import assert_success, build_demo_client


def test_risk_operator_can_score_accounts_and_acknowledge_alerts() -> None:
    client = build_demo_client("risk_operator_demo")

    score_payload = assert_success(
        client.post(
            "/risk/batch-score",
            json={"account_ids": ["acct-atlas-01", "acct-missing-00"]},
        )
    )
    assert score_payload["total_requested"] == 2
    assert score_payload["total_scored"] == 1
    assert score_payload["result_persistence"]["status"] in {"completed", "degraded"}

    status_payload = assert_success(
        client.post(
            "/ops/alerts/demo-alert/status",
            json={"status": "acknowledged"},
        )
    )
    assert status_payload["alert_id"] == "demo-alert"
    assert status_payload["update_status"] in {
        "completed",
        "not_found",
        "conflict",
        "failed",
    }


def test_risk_operator_cannot_close_alert_directly() -> None:
    client = build_demo_client("risk_operator_demo")

    response = client.post(
        "/ops/alerts/demo-alert/status",
        json={"status": "closed"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Risk operators may only acknowledge alerts directly."
    )


def test_analyst_cannot_use_risk_operator_workflow() -> None:
    client = build_demo_client("analyst_demo")

    response = client.post(
        "/risk/batch-score",
        json={"account_ids": ["acct-atlas-01"]},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role"
