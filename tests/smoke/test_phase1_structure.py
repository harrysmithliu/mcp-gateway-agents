from pathlib import Path


REQUIRED_PATHS = [
    "backend/api/app.py",
    "frontend/app.py",
    "sql/migrations/001_create_core_schemas.sql",
    "sql/migrations/002_create_phase1_core_tables.sql",
    "docs/PROJECT_REQUIREMENTS.md",
]


def test_phase1_required_paths_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    missing = [path for path in REQUIRED_PATHS if not (root / path).exists()]
    assert not missing, f"Missing Phase 1 paths: {missing}"

