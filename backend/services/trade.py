from dataclasses import dataclass

from backend.services.common import tokenize_text
from backend.services.demo_data import load_demo_dataset


@dataclass(frozen=True, slots=True)
class TradeMetricsSnapshot:
    snapshot_id: str
    account_id: str
    account_label: str
    wallet_id: str
    order_count_24h: int
    filled_notional_usd_24h: int
    net_exposure_usd: int
    concentration_ratio: float
    anomaly_flags: tuple[str, ...]
    keywords: tuple[str, ...]


DEFAULT_TRADE_METRICS_SNAPSHOTS = tuple(
    TradeMetricsSnapshot(
        snapshot_id=str(record["snapshot_id"]),
        account_id=str(record["account_id"]),
        account_label=str(record["account_label"]),
        wallet_id=str(record["wallet_id"]),
        order_count_24h=int(record["order_count_24h"]),
        filled_notional_usd_24h=int(record["filled_notional_usd_24h"]),
        net_exposure_usd=int(record["net_exposure_usd"]),
        concentration_ratio=float(record["concentration_ratio"]),
        anomaly_flags=tuple(str(flag) for flag in record["anomaly_flags"]),
        keywords=tuple(str(keyword) for keyword in record["keywords"]),
    )
    for record in load_demo_dataset("trade")
)


@dataclass(slots=True)
class TradeService:
    snapshots: tuple[TradeMetricsSnapshot, ...] = DEFAULT_TRADE_METRICS_SNAPSHOTS

    def get_metrics_by_account(
        self,
        account_id: str,
    ) -> dict[str, object] | None:
        for snapshot in self.snapshots:
            if snapshot.account_id != account_id:
                continue
            return {
                "snapshot_id": snapshot.snapshot_id,
                "account_id": snapshot.account_id,
                "account_label": snapshot.account_label,
                "wallet_id": snapshot.wallet_id,
                "order_count_24h": snapshot.order_count_24h,
                "filled_notional_usd_24h": snapshot.filled_notional_usd_24h,
                "net_exposure_usd": snapshot.net_exposure_usd,
                "concentration_ratio": snapshot.concentration_ratio,
                "anomaly_flags": list(snapshot.anomaly_flags),
            }
        return None

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
                    "account_id": snapshot.account_id,
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
