from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class TradeMetricWindow:
    account_id: str
    asset_symbol: str
    window_start: datetime
    window_end: datetime
    turnover_usd: float
    trade_count: int

