from functools import lru_cache
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_DATA_DIR = PROJECT_ROOT / "data" / "demo"

DEMO_DATASET_FILES = {
    "knowledge": "knowledge_records.json",
    "risk": "risk_account_profiles.json",
    "trade": "trade_metrics_snapshots.json",
    "operations": "ops_action_templates.json",
    "accounts": "account_domain_records.json",
}


def get_demo_data_path(dataset_name: str) -> Path:
    try:
        file_name = DEMO_DATASET_FILES[dataset_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported demo dataset: {dataset_name}") from exc
    return DEMO_DATA_DIR / file_name


@lru_cache(maxsize=None)
def load_demo_dataset(dataset_name: str) -> tuple[dict[str, Any], ...]:
    dataset_path = get_demo_data_path(dataset_name)
    if not dataset_path.exists():
        raise RuntimeError(f"Demo dataset is missing: {dataset_path}")

    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Demo dataset must be a JSON array: {dataset_path}")

    normalized_records: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise RuntimeError(f"Demo dataset item must be a JSON object: {dataset_path}")
        normalized_records.append(dict(item))
    return tuple(normalized_records)


def build_demo_seed_summary() -> dict[str, object]:
    datasets = {
        dataset_name: {
            "path": str(get_demo_data_path(dataset_name).relative_to(PROJECT_ROOT)),
            "record_count": len(load_demo_dataset(dataset_name)),
        }
        for dataset_name in DEMO_DATASET_FILES
    }
    return {
        "demo_data_dir": str(DEMO_DATA_DIR.relative_to(PROJECT_ROOT)),
        "datasets": datasets,
    }
