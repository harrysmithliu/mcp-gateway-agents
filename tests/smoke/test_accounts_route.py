import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_account_investigation_route_returns_composed_payload() -> None:
    client = TestClient(app)

    response = client.get("/accounts/acct-atlas-01/investigation")

    assert response.status_code == 200

    payload = response.json()
    assert payload["account_overview"]["account_id"] == "acct-atlas-01"
    assert payload["recent_activity"]["account_id"] == "acct-atlas-01"
    assert payload["risk_profile"]["account_id"] == "acct-atlas-01"
    assert payload["trade_metrics"]["account_id"] == "acct-atlas-01"


def test_account_search_route_returns_ranked_accounts() -> None:
    client = TestClient(app)

    response = client.post(
        "/accounts/search",
        json={"query": "atlas prime exposure", "limit": 3},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["query"] == "atlas prime exposure"
    assert payload["accounts"][0]["account_id"] == "acct-atlas-01"


def test_account_overview_route_returns_account_detail() -> None:
    client = TestClient(app)

    response = client.get("/accounts/acct-atlas-01/overview")

    assert response.status_code == 200

    payload = response.json()
    assert payload["account_id"] == "acct-atlas-01"
    assert payload["recent_orders"]
    assert payload["recent_trades"]


def test_account_activity_summary_route_returns_recent_activity() -> None:
    client = TestClient(app)

    response = client.get("/accounts/acct-atlas-01/activity-summary")

    assert response.status_code == 200

    payload = response.json()
    assert payload["account_id"] == "acct-atlas-01"
    assert payload["recent_order_count"] == 2
    assert payload["recent_trade_count"] == 2
