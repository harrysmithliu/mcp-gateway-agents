from dataclasses import dataclass

from backend.services.accounts import AccountDomainService
from backend.services.risk import RiskService
from backend.services.trade import TradeService


@dataclass(slots=True)
class AccountInvestigationService:
    account_domain_service: AccountDomainService
    risk_service: RiskService
    trade_service: TradeService

    def get_account_investigation(
        self,
        account_id: str,
    ) -> dict[str, object] | None:
        account_overview = self.account_domain_service.get_account_overview(account_id)
        if account_overview is None:
            return None

        return {
            "account_overview": account_overview,
            "recent_activity": self.account_domain_service.get_recent_activity_summary(
                account_id
            ),
            "risk_profile": self.risk_service.get_profile(account_id),
            "trade_metrics": self.trade_service.get_metrics_by_account(account_id),
        }
