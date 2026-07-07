import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_trade_account_metrics_route_returns_account_snapshot() -> None:
    client = TestClient(app)

    response = client.get("/trade/accounts/acct-atlas-01/metrics")

    assert response.status_code == 200

    payload = response.json()
    assert payload["account_id"] == "acct-atlas-01"
    assert payload["wallet_id"] == "wallet-atlas-01"
