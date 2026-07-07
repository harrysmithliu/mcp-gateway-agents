from dataclasses import asdict, dataclass

from backend.services.common import tokenize_text
from backend.services.demo_data import load_demo_dataset


@dataclass(frozen=True, slots=True)
class AccountBalance:
    asset: str
    available: float
    locked: float
    usd_value: float


@dataclass(frozen=True, slots=True)
class AccountPosition:
    symbol: str
    side: str
    quantity: float
    mark_price: float
    market_value_usd: float


@dataclass(frozen=True, slots=True)
class AccountOrder:
    order_id: str
    symbol: str
    side: str
    status: str
    order_type: str
    notional_usd: float
    created_at: str


@dataclass(frozen=True, slots=True)
class AccountTrade:
    trade_id: str
    symbol: str
    side: str
    quantity: float
    notional_usd: float
    executed_at: str


@dataclass(frozen=True, slots=True)
class AccountDomainRecord:
    account_id: str
    account_label: str
    customer_id: str
    account_type: str
    jurisdiction: str
    base_currency: str
    risk_level: str
    review_status: str
    anomaly_flags: tuple[str, ...]
    keywords: tuple[str, ...]
    balances: tuple[AccountBalance, ...]
    positions: tuple[AccountPosition, ...]
    recent_orders: tuple[AccountOrder, ...]
    recent_trades: tuple[AccountTrade, ...]


def _build_account_balance(payload: dict[str, object]) -> AccountBalance:
    return AccountBalance(
        asset=str(payload["asset"]),
        available=float(payload["available"]),
        locked=float(payload["locked"]),
        usd_value=float(payload["usd_value"]),
    )


def _build_account_position(payload: dict[str, object]) -> AccountPosition:
    return AccountPosition(
        symbol=str(payload["symbol"]),
        side=str(payload["side"]),
        quantity=float(payload["quantity"]),
        mark_price=float(payload["mark_price"]),
        market_value_usd=float(payload["market_value_usd"]),
    )


def _build_account_order(payload: dict[str, object]) -> AccountOrder:
    return AccountOrder(
        order_id=str(payload["order_id"]),
        symbol=str(payload["symbol"]),
        side=str(payload["side"]),
        status=str(payload["status"]),
        order_type=str(payload["order_type"]),
        notional_usd=float(payload["notional_usd"]),
        created_at=str(payload["created_at"]),
    )


def _build_account_trade(payload: dict[str, object]) -> AccountTrade:
    return AccountTrade(
        trade_id=str(payload["trade_id"]),
        symbol=str(payload["symbol"]),
        side=str(payload["side"]),
        quantity=float(payload["quantity"]),
        notional_usd=float(payload["notional_usd"]),
        executed_at=str(payload["executed_at"]),
    )


def _build_account_domain_record(payload: dict[str, object]) -> AccountDomainRecord:
    return AccountDomainRecord(
        account_id=str(payload["account_id"]),
        account_label=str(payload["account_label"]),
        customer_id=str(payload["customer_id"]),
        account_type=str(payload["account_type"]),
        jurisdiction=str(payload["jurisdiction"]),
        base_currency=str(payload["base_currency"]),
        risk_level=str(payload["risk_level"]),
        review_status=str(payload["review_status"]),
        anomaly_flags=tuple(str(flag) for flag in payload["anomaly_flags"]),
        keywords=tuple(str(keyword) for keyword in payload["keywords"]),
        balances=tuple(
            _build_account_balance(balance)
            for balance in payload["balances"]
        ),
        positions=tuple(
            _build_account_position(position)
            for position in payload["positions"]
        ),
        recent_orders=tuple(
            _build_account_order(order)
            for order in payload["recent_orders"]
        ),
        recent_trades=tuple(
            _build_account_trade(trade)
            for trade in payload["recent_trades"]
        ),
    )


DEFAULT_ACCOUNT_DOMAIN_RECORDS = tuple(
    _build_account_domain_record(record)
    for record in load_demo_dataset("accounts")
)


@dataclass(slots=True)
class AccountDomainService:
    records: tuple[AccountDomainRecord, ...] = DEFAULT_ACCOUNT_DOMAIN_RECORDS

    def list_accounts(self) -> tuple[AccountDomainRecord, ...]:
        return self.records

    def get_account(self, account_id: str) -> AccountDomainRecord | None:
        for record in self.records:
            if record.account_id == account_id:
                return record
        return None

    def search_accounts(
        self,
        query_text: str,
        limit: int = 5,
    ) -> dict[str, object]:
        query_terms = tokenize_text(query_text)
        ranked_matches = []

        for record in self.records:
            matched_terms = sorted(query_terms.intersection(record.keywords))
            if not matched_terms:
                continue

            ranked_matches.append(
                {
                    "account_id": record.account_id,
                    "account_label": record.account_label,
                    "customer_id": record.customer_id,
                    "account_type": record.account_type,
                    "jurisdiction": record.jurisdiction,
                    "base_currency": record.base_currency,
                    "risk_level": record.risk_level,
                    "review_status": record.review_status,
                    "anomaly_flags": list(record.anomaly_flags),
                    "balance_count": len(record.balances),
                    "position_count": len(record.positions),
                    "recent_order_count": len(record.recent_orders),
                    "recent_trade_count": len(record.recent_trades),
                    "matched_terms": matched_terms,
                    "match_score": len(matched_terms),
                }
            )

        ranked_matches.sort(
            key=lambda item: (
                item["match_score"],
                item["risk_level"] == "high",
                item["risk_level"] == "medium",
            ),
            reverse=True,
        )
        top_matches = ranked_matches[:limit]

        return {
            "query": query_text,
            "total_matches": len(top_matches),
            "accounts": top_matches,
        }
    
    def get_account_overview(self, account_id: str) -> dict[str, object] | None:
        record = self.get_account(account_id)
        if not record:
            return None

        return {
            "account_id": record.account_id,
            "account_label": record.account_label,
            "customer_id": record.customer_id,
            "account_type": record.account_type,
            "jurisdiction": record.jurisdiction,
            "base_currency": record.base_currency,
            "risk_level": record.risk_level,
            "review_status": record.review_status,
            "anomaly_flags": list(record.anomaly_flags),
            "balances": [asdict(balance) for balance in record.balances],
            "positions": [asdict(position) for position in record.positions],
            "balance_count": len(record.balances),
            "position_count": len(record.positions),
            "recent_orders": [asdict(order) for order in record.recent_orders],
            "recent_trades": [asdict(trade) for trade in record.recent_trades],
            "total_balance_usd": sum(balance.usd_value for balance in record.balances),
            "total_position_market_value_usd": sum(position.market_value_usd for position in record.positions),
        }