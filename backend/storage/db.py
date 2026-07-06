from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Minimal database configuration boundary for PostgreSQL persistence."""

    database_url: str
    connect_timeout_seconds: int = 5


@dataclass(frozen=True, slots=True)
class SQLStatement:
    """Portable SQL statement envelope for repository writes."""

    sql: str
    params: dict[str, object]


@dataclass(slots=True)
class DatabaseClient:
    """Lazy PostgreSQL client wrapper so the codebase can load without a driver."""

    config: DatabaseConfig

    def _import_psycopg(self) -> Any:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "psycopg is required for PostgreSQL persistence at runtime."
            ) from exc
        return psycopg

    @contextmanager
    def connect(self) -> Iterator[Any]:
        psycopg = self._import_psycopg()
        connection = psycopg.connect(
            self.config.database_url,
            connect_timeout=self.config.connect_timeout_seconds,
        )
        try:
            yield connection
        finally:
            connection.close()

    def execute(self, statement: SQLStatement) -> None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement.sql, statement.params)
            connection.commit()
