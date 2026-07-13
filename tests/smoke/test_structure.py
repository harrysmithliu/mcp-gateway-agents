from pathlib import Path


REQUIRED_PATHS = [
    "backend/api/app.py",
    "backend/retrieval/service.py",
    "backend/services/operations.py",
    "frontend/app.py",
    "sql/migrations/001_create_core_schemas.sql",
    "sql/migrations/002_create_core_operational_tables.sql",
    "sql/migrations/005_create_rag_tables.sql",
    "sql/migrations/006_upgrade_chunk_embeddings_to_384.sql",
    "sql/migrations/007_create_risk_batch_score_tables.sql",
    "sql/migrations/008_create_risk_alert_status_events.sql",
    "sql/migrations/009_create_auth_tables.sql",
    "docs/PROJECT_REQUIREMENTS.md",
    "scripts/verify_round5_persistence.py",
]


def test_required_paths_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    missing = [path for path in REQUIRED_PATHS if not (root / path).exists()]
    assert not missing, f"Missing required paths: {missing}"


def test_deprecated_integration_tools_module_removed() -> None:
    root = Path(__file__).resolve().parents[2]
    assert not (root / "integrations/tools").exists()
