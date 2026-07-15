import sys
from contextlib import contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.bootstrap import apply_local_sql_plan, build_local_sql_plan


class _FakeCursor:
    def __init__(self) -> None:
        self.applied_scripts: set[tuple[str, str]] = set()
        self._selected_script: tuple[str, str] | None = None
        self.executed_sql: list[str] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[str, str] | None = None) -> None:
        self.executed_sql.append(sql)
        if "SELECT 1" in sql:
            self._selected_script = params
        elif "INSERT INTO public.local_sql_scripts" in sql:
            assert params is not None
            self.applied_scripts.add(params)

    def fetchone(self) -> tuple[int] | None:
        if self._selected_script in self.applied_scripts:
            return (1,)
        return None


class _FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = _FakeCursor()
        self.commit_count = 0

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


class _FakeDatabaseClient:
    def __init__(self) -> None:
        self.connection = _FakeConnection()

    @contextmanager
    def connect(self):
        yield self.connection


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


def test_apply_local_sql_plan_skips_scripts_recorded_as_applied(tmp_path: Path) -> None:
    sql_root = tmp_path / "sql"
    migrations_root = sql_root / "migrations"
    seeds_root = sql_root / "seeds"
    migrations_root.mkdir(parents=True)
    seeds_root.mkdir()
    (migrations_root / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (seeds_root / "001_first.sql").write_text("SELECT 2;", encoding="utf-8")

    database_client = _FakeDatabaseClient()
    plan = build_local_sql_plan(tmp_path)

    first_run = apply_local_sql_plan(database_client, plan)
    second_run = apply_local_sql_plan(database_client, plan)

    assert first_run == ["001_first.sql", "001_first.sql"]
    assert second_run == []
    assert database_client.connection.commit_count == 2
    assert database_client.connection.cursor_instance.executed_sql.count("SELECT 1;") == 1
    assert database_client.connection.cursor_instance.executed_sql.count("SELECT 2;") == 1
