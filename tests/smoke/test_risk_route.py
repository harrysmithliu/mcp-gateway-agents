import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_risk_batch_score_route_returns_aggregate_summary() -> None:
    client = TestClient(app)

    response = client.post(
        "/risk/batch-score",
        json={"account_ids": ["acct-atlas-01", "acct-gamma-88", "acct-missing-00"]},
        headers={"x-demo-user": "risk_operator_demo"},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["total_requested"] == 3
    assert payload["total_scored"] == 2
    assert payload["profiles"][0]["account_id"] == "acct-atlas-01"
    assert payload["result_persistence"]["status"] == "not_persisted"
