from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.bootstrap import apply_local_sql_plan, build_local_sql_plan
from backend.storage.db import DatabaseClient, DatabaseConfig
from backend.storage.settings import get_settings


def main() -> int:
    settings = get_settings()
    sql_plan = build_local_sql_plan(PROJECT_ROOT)
    database_client = DatabaseClient(
        DatabaseConfig(database_url=settings.database_url)
    )
    try:
        applied_files = apply_local_sql_plan(database_client, sql_plan)
    except Exception as exc:
        raise RuntimeError(
            "Unable to apply local SQL state. Verify PostgreSQL is running and DATABASE_URL is reachable."
        ) from exc
    print(
        json.dumps(
            {
                "database_url": settings.database_url,
                "applied_files": applied_files,
                "migration_count": len(sql_plan.migrations),
                "seed_count": len(sql_plan.seeds),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
