from dataclasses import dataclass
from pathlib import Path

from backend.storage.db import DatabaseClient


@dataclass(frozen=True, slots=True)
class LocalSQLPlan:
    migrations: tuple[Path, ...]
    seeds: tuple[Path, ...]

    @property
    def all_files(self) -> tuple[Path, ...]:
        return self.migrations + self.seeds


def build_local_sql_plan(project_root: Path) -> LocalSQLPlan:
    sql_root = project_root / "sql"
    migrations = tuple(sorted((sql_root / "migrations").glob("*.sql")))
    seeds = tuple(sorted((sql_root / "seeds").glob("*.sql")))
    return LocalSQLPlan(migrations=migrations, seeds=seeds)


def apply_local_sql_plan(
    database_client: DatabaseClient,
    plan: LocalSQLPlan,
) -> list[str]:
    applied_files: list[str] = []
    with database_client.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS public.local_sql_scripts (
                    script_type TEXT NOT NULL,
                    script_name TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (script_type, script_name)
                )
                """
            )
            script_groups = (
                ("migration", plan.migrations),
                ("seed", plan.seeds),
            )
            for script_type, sql_files in script_groups:
                for sql_file in sql_files:
                    cursor.execute(
                        """
                        SELECT 1
                        FROM public.local_sql_scripts
                        WHERE script_type = %s AND script_name = %s
                        """,
                        (script_type, sql_file.name),
                    )
                    if cursor.fetchone() is not None:
                        continue
                    cursor.execute(sql_file.read_text(encoding="utf-8"))
                    cursor.execute(
                        """
                        INSERT INTO public.local_sql_scripts (script_type, script_name)
                        VALUES (%s, %s)
                        """,
                        (script_type, sql_file.name),
                    )
                    applied_files.append(sql_file.name)
        connection.commit()
    return applied_files
