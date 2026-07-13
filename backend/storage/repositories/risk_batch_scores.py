from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import RiskBatchScoreResultRecord, RiskBatchScoreRunRecord
from backend.storage.repositories.base import StatementExecutor


@dataclass(slots=True)
class RiskBatchScoreRepository:
    executor: StatementExecutor

    def build_run_statement(self, record: RiskBatchScoreRunRecord) -> SQLStatement:
        return SQLStatement(
            sql=(
                "INSERT INTO risk.batch_score_runs "
                "(run_id, actor_user_id, requested_account_count, scored_account_count, "
                "missing_account_count, highest_risk_score, average_risk_score, "
                "risk_level_counts) "
                "VALUES ("
                "%(run_id)s, %(actor_user_id)s, %(requested_account_count)s, "
                "%(scored_account_count)s, %(missing_account_count)s, "
                "%(highest_risk_score)s, %(average_risk_score)s, %(risk_level_counts)s"
                ")"
            ),
            params={
                "run_id": record.run_id,
                "actor_user_id": record.actor_user_id,
                "requested_account_count": record.requested_account_count,
                "scored_account_count": record.scored_account_count,
                "missing_account_count": record.missing_account_count,
                "highest_risk_score": record.highest_risk_score,
                "average_risk_score": record.average_risk_score,
                "risk_level_counts": record.risk_level_counts,
            },
        )

    def create_run(self, record: RiskBatchScoreRunRecord) -> SQLStatement:
        statement = self.build_run_statement(record)
        self.executor.execute(statement)
        return statement

    def build_result_statement(
        self,
        record: RiskBatchScoreResultRecord,
    ) -> SQLStatement:
        return SQLStatement(
            sql=(
                "INSERT INTO risk.batch_score_results "
                "(result_id, run_id, account_id, profile_id, risk_score, risk_level, "
                "review_status, exposure_usd, alert_count_30d, risk_flags) "
                "VALUES ("
                "%(result_id)s, %(run_id)s, %(account_id)s, %(profile_id)s, "
                "%(risk_score)s, %(risk_level)s, %(review_status)s, %(exposure_usd)s, "
                "%(alert_count_30d)s, %(risk_flags)s"
                ")"
            ),
            params={
                "result_id": record.result_id,
                "run_id": record.run_id,
                "account_id": record.account_id,
                "profile_id": record.profile_id,
                "risk_score": record.risk_score,
                "risk_level": record.risk_level,
                "review_status": record.review_status,
                "exposure_usd": record.exposure_usd,
                "alert_count_30d": record.alert_count_30d,
                "risk_flags": record.risk_flags,
            },
        )

    def create_result(self, record: RiskBatchScoreResultRecord) -> SQLStatement:
        statement = self.build_result_statement(record)
        self.executor.execute(statement)
        return statement

    def get_run(self, run_id: str) -> dict[str, object] | None:
        rows = self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT run_id, actor_user_id, requested_account_count, "
                    "scored_account_count, missing_account_count, highest_risk_score, "
                    "average_risk_score, risk_level_counts, created_at "
                    "FROM risk.batch_score_runs WHERE run_id = %(run_id)s"
                ),
                params={"run_id": run_id},
            )
        )
        return rows[0] if rows else None

    def list_results(self, run_id: str) -> list[dict[str, object]]:
        return self.executor.fetch_all(
            SQLStatement(
                sql=(
                    "SELECT result_id, run_id, account_id, profile_id, risk_score, "
                    "risk_level, review_status, exposure_usd, alert_count_30d, "
                    "risk_flags, created_at "
                    "FROM risk.batch_score_results "
                    "WHERE run_id = %(run_id)s ORDER BY account_id"
                ),
                params={"run_id": run_id},
            )
        )
