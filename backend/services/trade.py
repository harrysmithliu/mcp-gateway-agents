from dataclasses import dataclass

from backend.services.common import tokenize_text


@dataclass(frozen=True, slots=True)
class TradeMetricsSnapshot:
    snapshot_id: str
    account_label: str
    wallet_id: str
    order_count_24h: int
    filled_notional_usd_24h: int
    net_exposure_usd: int
    concentration_ratio: float
    anomaly_flags: tuple[str, ...]
    keywords: tuple[str, ...]


DEFAULT_TRADE_METRICS_SNAPSHOTS = (
    TradeMetricsSnapshot(
        snapshot_id="trade-snapshot-alpha",
        account_label="Alpha Market Maker",
        wallet_id="wallet-alpha-01",
        order_count_24h=184,
        filled_notional_usd_24h=2450000,
        net_exposure_usd=320000,
        concentration_ratio=0.41,
        anomaly_flags=("exposure_shift",),
        keywords=("trade", "wallet", "volume", "market", "maker", "alpha"),
    ),
    TradeMetricsSnapshot(
        snapshot_id="trade-snapshot-beta",
        account_label="Beta Treasury Wallet",
        wallet_id="wallet-beta-17",
        order_count_24h=42,
        filled_notional_usd_24h=780000,
        net_exposure_usd=110000,
        concentration_ratio=0.28,
        anomaly_flags=("none",),
        keywords=("trade", "wallet", "treasury", "beta", "exposure"),
    ),
    TradeMetricsSnapshot(
        snapshot_id="trade-snapshot-gamma",
        account_label="Gamma High-Volume Desk",
        wallet_id="wallet-gamma-88",
        order_count_24h=267,
        filled_notional_usd_24h=3910000,
        net_exposure_usd=540000,
        concentration_ratio=0.57,
        anomaly_flags=("volume_spike", "concentration_risk"),
        keywords=("trade", "wallet", "order", "volume", "gamma", "desk"),
    ),
)


@dataclass(slots=True)
class TradeService:
    snapshots: tuple[TradeMetricsSnapshot, ...] = DEFAULT_TRADE_METRICS_SNAPSHOTS

    def query_metrics(
        self,
        query_text: str,
        limit: int = 3,
    ) -> dict[str, object]:
        query_terms = tokenize_text(query_text)
        ranked_snapshots = []

        for snapshot in self.snapshots:
            matched_terms = sorted(query_terms.intersection(snapshot.keywords))
            if not matched_terms:
                continue

            ranked_snapshots.append(
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "account_label": snapshot.account_label,
                    "wallet_id": snapshot.wallet_id,
                    "order_count_24h": snapshot.order_count_24h,
                    "filled_notional_usd_24h": snapshot.filled_notional_usd_24h,
                    "net_exposure_usd": snapshot.net_exposure_usd,
                    "concentration_ratio": snapshot.concentration_ratio,
                    "anomaly_flags": list(snapshot.anomaly_flags),
                    "matched_terms": matched_terms,
                    "match_score": len(matched_terms),
                }
            )

        ranked_snapshots.sort(
            key=lambda snapshot: (
                snapshot["match_score"],
                snapshot["filled_notional_usd_24h"],
            ),
            reverse=True,
        )
        top_snapshots = ranked_snapshots[:limit]

        return {
            "query": query_text,
            "total_matches": len(top_snapshots),
            "total_filled_notional_usd_24h": sum(
                snapshot["filled_notional_usd_24h"] for snapshot in top_snapshots
            ),
            "max_concentration_ratio": max(
                (snapshot["concentration_ratio"] for snapshot in top_snapshots),
                default=0.0,
            ),
            "snapshots": top_snapshots,
        }
