from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.audit import AuditService
from backend.services.ops_workflow import OpsWorkflowService
from backend.services.risk import RiskService
from backend.services.risk_batch import RiskBatchScoreService
from backend.storage.bootstrap import apply_local_sql_plan, build_local_sql_plan
from backend.storage.models import RiskAlertRecord
from backend.storage.runtime import build_storage_bundle
from backend.storage.settings import get_settings


def main() -> int:
    settings = get_settings()
    storage_bundle = build_storage_bundle(settings)
    sql_plan = build_local_sql_plan(PROJECT_ROOT)
    applied_files = apply_local_sql_plan(
        storage_bundle.database_client,
        sql_plan,
    )

    risk_batch_service = RiskBatchScoreService(
        risk_service=RiskService(),
        risk_batch_score_repository=storage_bundle.risk_batch_score_repository,
        database_client=storage_bundle.database_client,
    )
    batch_payload = risk_batch_service.score_accounts_batch(
        ["acct-atlas-01", "acct-gamma-88", "acct-missing-00"]
    )
    if batch_payload["result_persistence"]["status"] != "completed":
        raise RuntimeError("Risk batch score persistence did not complete.")

    run_id = str(batch_payload["run_id"])
    persisted_run = storage_bundle.risk_batch_score_repository.get_run(run_id)
    persisted_results = storage_bundle.risk_batch_score_repository.list_results(run_id)
    if persisted_run is None or len(persisted_results) != batch_payload["total_scored"]:
        raise RuntimeError("Risk batch score records could not be read back.")

    alert_id = str(uuid4())
    storage_bundle.risk_alert_repository.create_risk_alert(
        RiskAlertRecord(
            alert_id=alert_id,
            alert_type="round5_verification",
            severity="medium",
            status="open",
            summary="Round 5 persistence verification alert.",
            details={"run_id": run_id},
        )
    )
    transition_payload = OpsWorkflowService(storage_bundle).update_alert_status(
        alert_id=alert_id,
        status="acknowledged",
    )
    if transition_payload["update_status"] != "completed":
        raise RuntimeError("Risk alert status transition did not complete.")

    status_history = storage_bundle.risk_alert_status_event_repository.list_for_alert(
        alert_id
    )
    audit_payload = AuditService(storage_bundle).list_recent_events(
        event_type="risk_alert_status_changed"
    )
    if not status_history or audit_payload["query_status"] != "completed":
        raise RuntimeError("Risk alert history or audit readback failed.")

    print(
        json.dumps(
            {
                "applied_file_count": len(applied_files),
                "migration_count": len(sql_plan.migrations),
                "seed_count": len(sql_plan.seeds),
                "risk_batch": {
                    "run_id": run_id,
                    "requested": batch_payload["total_requested"],
                    "scored": batch_payload["total_scored"],
                    "persisted_results": len(persisted_results),
                },
                "risk_alert": {
                    "alert_id": alert_id,
                    "status": transition_payload["status"],
                    "status_history_count": len(status_history),
                },
                "audit": {
                    "query_status": audit_payload["query_status"],
                    "matching_events": len(audit_payload["events"]),
                },
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
