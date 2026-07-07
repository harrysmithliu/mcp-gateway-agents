from typing import Protocol

from backend.storage.db import SQLStatement


class StatementExecutor(Protocol):
    """Minimal executor protocol so repositories stay testable without a DB."""

    def execute(self, statement: SQLStatement) -> None: ...
    def fetch_all(self, statement: SQLStatement) -> list[dict[str, object]]: ...
