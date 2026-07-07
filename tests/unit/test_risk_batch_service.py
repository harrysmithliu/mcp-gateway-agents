from backend.services.risk import RiskService


def test_risk_service_score_accounts_batch_returns_aggregate_summary() -> None:
    service = RiskService()

    response_payload = service.score_accounts_batch(
        ["acct-atlas-01", "acct-gamma-88", "acct-missing-00"]
    )

    assert response_payload["total_requested"] == 3
    assert response_payload["total_scored"] == 2
    assert response_payload["missing_account_ids"] == ["acct-missing-00"]
    assert response_payload["highest_risk_score"] == 82
    assert response_payload["risk_level_counts"]["high"] == 1
    assert response_payload["risk_level_counts"]["medium"] == 1
    assert response_payload["result_persistence"]["status"] == "not_persisted"
