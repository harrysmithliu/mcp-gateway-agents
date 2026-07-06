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
            for sql_file in plan.all_files:
                cursor.execute(sql_file.read_text(encoding="utf-8"))
                applied_files.append(sql_file.name)
        connection.commit()
    return applied_files
