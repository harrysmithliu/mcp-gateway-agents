import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.bootstrap import build_local_sql_plan


def test_build_local_sql_plan_returns_sorted_migrations_and_seeds() -> None:
    plan = build_local_sql_plan(PROJECT_ROOT)

    assert [path.name for path in plan.migrations] == [
        "001_create_core_schemas.sql",
        "002_create_core_operational_tables.sql",
        "003_create_risk_alerts_table.sql",
        "004_allow_nullable_chat_session_user_id.sql",
        "005_create_rag_tables.sql",
        "006_upgrade_chunk_embeddings_to_384.sql",
        "007_create_risk_batch_score_tables.sql",
        "008_create_risk_alert_status_events.sql",
        "009_create_auth_tables.sql",
        "010_create_risk_alert_approvals.sql",
        "011_create_knowledge_ingestion_runs.sql",
        "012_add_knowledge_revision_metadata.sql",
    ]
    assert [path.name for path in plan.seeds] == [
        "001_seed_roles.sql",
        "002_seed_demo_users.sql",
    ]
