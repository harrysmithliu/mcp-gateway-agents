from backend.services.account_investigation import AccountInvestigationService
from backend.services.accounts import AccountDomainService
from backend.services.risk import RiskService
from backend.services.trade import TradeService


def test_account_investigation_service_returns_composed_payload() -> None:
    service = AccountInvestigationService(
        account_domain_service=AccountDomainService(),
        risk_service=RiskService(),
        trade_service=TradeService(),
    )

    response_payload = service.get_account_investigation("acct-atlas-01")

    assert response_payload is not None
    assert response_payload["account_overview"]["account_id"] == "acct-atlas-01"
    assert response_payload["recent_activity"]["account_id"] == "acct-atlas-01"
    assert response_payload["risk_profile"]["account_id"] == "acct-atlas-01"
    assert response_payload["trade_metrics"]["account_id"] == "acct-atlas-01"
