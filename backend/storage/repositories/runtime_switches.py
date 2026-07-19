from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class RuntimeSwitchRepository:
    executor: StatementExecutor

    def list_runtime_switches(self) -> list[dict[str, object]]:
        return self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT switch_key, is_enabled, updated_by_user_id, updated_at "
                    "FROM iam.runtime_switches ORDER BY switch_key"
                ),
                params={},
            )
        )

    @staticmethod
    def build_set_statement(
        *,
        switch_key: str,
        is_enabled: bool,
        actor_user_id: int,
    ) -> SQLStatement:
        return SQLStatement(
            sql=(
                "INSERT INTO iam.runtime_switches "
                "(switch_key, is_enabled, updated_by_user_id) "
                "VALUES (%(switch_key)s, %(is_enabled)s, %(actor_user_id)s) "
                "ON CONFLICT (switch_key) DO UPDATE SET "
                "is_enabled = EXCLUDED.is_enabled, "
                "updated_by_user_id = EXCLUDED.updated_by_user_id, "
                "updated_at = NOW()"
            ),
            params={
                "switch_key": switch_key,
                "is_enabled": is_enabled,
                "actor_user_id": actor_user_id,
            },
        )
