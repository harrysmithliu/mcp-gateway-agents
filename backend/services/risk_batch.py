from dataclasses import dataclass
from uuid import uuid4

from backend.services.risk import RiskService
from backend.storage.db import DatabaseClient
from backend.storage.models import RiskBatchScoreResultRecord, RiskBatchScoreRunRecord
from backend.storage.repositories.risk_batch_scores import RiskBatchScoreRepository


@dataclass(slots=True)
class RiskBatchScoreService:
    """Coordinates pure risk scoring with one transactional persistence write."""

    risk_service: RiskService
    risk_batch_score_repository: RiskBatchScoreRepository
    database_client: DatabaseClient

    def score_accounts_batch(self, account_ids: list[str]) -> dict[str, object]:
        scoring_payload = self.risk_service.score_accounts_batch(account_ids)
        run_id = str(uuid4())
        profiles = scoring_payload["profiles"]
        if not isinstance(profiles, list):
            raise RuntimeError("Risk scoring returned an invalid profile collection.")

        run_record = RiskBatchScoreRunRecord(
            run_id=run_id,
            requested_account_count=int(scoring_payload["total_requested"]),
            scored_account_count=int(scoring_payload["total_scored"]),
            missing_account_count=len(scoring_payload["missing_account_ids"]),
            highest_risk_score=int(scoring_payload["highest_risk_score"]),
            average_risk_score=float(scoring_payload["average_risk_score"]),
            risk_level_counts=dict(scoring_payload["risk_level_counts"]),
        )
        result_records = [
            RiskBatchScoreResultRecord(
                result_id=str(uuid4()),
                run_id=run_id,
                account_id=str(profile["account_id"]),
                profile_id=str(profile["profile_id"]),
                risk_score=int(profile["risk_score"]),
                risk_level=str(profile["risk_level"]),
                review_status=str(profile["review_status"]),
                exposure_usd=int(profile["exposure_usd"]),
                alert_count_30d=int(profile["alert_count_30d"]),
                risk_flags=[str(flag) for flag in profile["risk_flags"]],
            )
            for profile in profiles
        ]

        try:
            with self.database_client.transaction() as transaction:
                transaction.execute(
                    self.risk_batch_score_repository.build_run_statement(run_record)
                )
                for result_record in result_records:
                    transaction.execute(
                        self.risk_batch_score_repository.build_result_statement(result_record)
                    )
        except Exception:
            return {
                **scoring_payload,
                "run_id": run_id,
                "result_persistence": {
                    "status": "degraded",
                    "reason": "batch_score_write_failed",
                    "run_id": run_id,
                },
            }

        return {
            **scoring_payload,
            "run_id": run_id,
            "result_persistence": {
                "status": "completed",
                "run_id": run_id,
                "result_count": len(result_records),
            },
        }
