from __future__ import annotations

# ruff: noqa: E402

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.bootstrap import apply_local_sql_plan, build_local_sql_plan
from backend.storage.db import DatabaseClient, DatabaseConfig
from backend.storage.reset import (
    LocalResetService,
    LocalResetTarget,
    RedisScopedReset,
    ResetScope,
    build_local_reset_plan,
)
from backend.storage.settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or explicitly reset project-owned local runtime state."
    )
    parser.add_argument(
        "--scope",
        choices=[scope.value for scope in ResetScope],
        default=ResetScope.RUNTIME.value,
        help="runtime clears transient state; demo also clears identities and knowledge.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="execute the reset after target validation; omitted means dry-run.",
    )
    return parser


def build_target() -> LocalResetTarget:
    settings = get_settings()
    return LocalResetTarget(
        app_env=settings.app_env,
        database_url=settings.database_url,
        redis_url=settings.redis_url,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scope = ResetScope(args.scope)
    settings = get_settings()
    target = build_target()
    target.validate()
    plan = build_local_reset_plan(
        scope=scope,
        response_cache_key_prefix=settings.response_cache_key_prefix,
    )

    if not args.confirm:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "target": target.redacted_payload(),
                    "plan": plan.to_payload(),
                    "next_step": "rerun with --confirm to execute",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    database_client = DatabaseClient(
        DatabaseConfig(database_url=settings.database_url)
    )
    sql_plan = build_local_sql_plan(PROJECT_ROOT)
    applied_before_reset = apply_local_sql_plan(database_client, sql_plan)
    service = LocalResetService(
        database_client=database_client,
        redis_reset=RedisScopedReset(redis_url=settings.redis_url),
    )
    report = service.execute(plan)
    reapplied_seed_files: list[str] = []
    if plan.release_seed_ledger:
        reapplied_seed_files = apply_local_sql_plan(database_client, sql_plan)

    status = "partial_failure" if report.redis_error is not None else "succeeded"
    print(
        json.dumps(
            {
                "status": status,
                "target": target.redacted_payload(),
                "applied_before_reset": applied_before_reset,
                "report": report.to_payload(),
                "reapplied_seed_files": reapplied_seed_files,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if report.redis_error is not None else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit(f"Local reset failed: {exc}") from exc
