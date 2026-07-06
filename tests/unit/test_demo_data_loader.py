import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.demo_data import build_demo_seed_summary, load_demo_dataset


def test_load_demo_dataset_returns_expected_trade_records() -> None:
    trade_records = load_demo_dataset("trade")

    assert len(trade_records) == 3
    assert trade_records[0]["snapshot_id"] == "trade-snapshot-alpha"
    assert trade_records[-1]["wallet_id"] == "wallet-gamma-88"


def test_build_demo_seed_summary_reports_all_demo_datasets() -> None:
    summary = build_demo_seed_summary()

    assert summary["demo_data_dir"] == "data/demo"
    datasets = summary["datasets"]
    assert set(datasets) == {"knowledge", "operations", "risk", "trade"}
    assert datasets["knowledge"]["record_count"] >= 1
    assert datasets["trade"]["path"] == "data/demo/trade_metrics_snapshots.json"
