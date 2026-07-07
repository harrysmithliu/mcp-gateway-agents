from backend.services.accounts import AccountDomainService


def test_account_domain_service_loads_demo_records() -> None:
    service = AccountDomainService()
    records = service.list_accounts()

    assert len(records) >= 3
    assert records[0].account_id
    assert records[0].balances


def test_account_domain_service_get_account_returns_record() -> None:
    service = AccountDomainService()
    
    record = service.get_account("acct-atlas-01")

    assert record is not None
    assert record.account_label == "Atlas Prime Borrower"
    assert record.risk_level == "high"


def test_account_domain_service_search_accounts_returns_ranked_matches() -> None:
    service = AccountDomainService()

    response_payload = service.search_accounts(
        query_text="atlas prime account exposure risk",
        limit=3,
    )

    assert response_payload["query"] == "atlas prime account exposure risk"
    assert response_payload["total_matches"] >= 1
    assert response_payload["accounts"]
    assert response_payload["accounts"][0]["account_id"] == "acct-atlas-01"


def test_account_domain_service_get_account_overview_returns_detail_payload() -> None:
    service = AccountDomainService()

    response_payload = service.get_account_overview("acct-atlas-01")

    assert response_payload is not None
    assert response_payload["account_id"] == "acct-atlas-01"
    assert response_payload["account_label"] == "Atlas Prime Borrower"
    assert response_payload["balances"]
    assert response_payload["positions"]
    assert response_payload["recent_orders"]
    assert response_payload["recent_trades"]
    assert response_payload["total_balance_usd"] > 0
    assert response_payload["total_position_market_value_usd"] > 0
