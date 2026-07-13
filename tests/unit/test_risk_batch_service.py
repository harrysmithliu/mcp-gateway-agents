from contextlib import contextmanager

from backend.services.risk import RiskService
from backend.services.risk_batch import RiskBatchScoreService
from backend.storage.db import SQLStatement


class FakeTransaction:
    def __init__(self) -> None:
        self.statements: list[SQLStatement] = []

    def execute(self, statement: SQLStatement) -> None:
        self.statements.append(statement)


class FakeDatabaseClient:
    def __init__(self) -> None:
        self.transaction_statements: list[SQLStatement] = []

    @contextmanager
    def transaction(self):
        transaction = FakeTransaction()
        yield transaction
        self.transaction_statements.extend(transaction.statements)


class FakeRiskBatchScoreRepository:
    def build_run_statement(self, record):
        return SQLStatement("INSERT run", {"run_id": record.run_id})

    def build_result_statement(self, record):
        return SQLStatement("INSERT result", {"result_id": record.result_id})


def test_risk_service_score_accounts_batch_returns_aggregate_summary() -> None:
    service = RiskService()

    response_payload = service.score_accounts_batch(
        ["acct-atlas-01", "acct-gamma-88", "acct-missing-00"]
    )

    assert response_payload["total_requested"] == 3
    assert response_payload["total_scored"] == 2
    assert response_payload["missing_account_ids"] == ["acct-missing-00"]
    assert response_payload["highest_risk_score"] == 82
    assert response_payload["risk_level_counts"]["high"] == 1
    assert response_payload["risk_level_counts"]["medium"] == 1
    assert "result_persistence" not in response_payload


def test_risk_batch_score_service_persists_run_and_results_transactionally() -> None:
    database_client = FakeDatabaseClient()
    service = RiskBatchScoreService(
        risk_service=RiskService(),
        risk_batch_score_repository=FakeRiskBatchScoreRepository(),
        database_client=database_client,
    )

    response_payload = service.score_accounts_batch(
        ["acct-atlas-01", "acct-gamma-88", "acct-missing-00"]
    )

    assert response_payload["result_persistence"]["status"] == "completed"
    assert response_payload["result_persistence"]["result_count"] == 2
    assert len(database_client.transaction_statements) == 3
    assert database_client.transaction_statements[0].sql == "INSERT run"
    assert all(
        statement.sql == "INSERT result"
        for statement in database_client.transaction_statements[1:]
    )


def test_risk_batch_score_service_reports_degraded_write() -> None:
    class FailingDatabaseClient(FakeDatabaseClient):
        @contextmanager
        def transaction(self):
            raise RuntimeError("database unavailable")
            yield

    service = RiskBatchScoreService(
        risk_service=RiskService(),
        risk_batch_score_repository=FakeRiskBatchScoreRepository(),
        database_client=FailingDatabaseClient(),
    )

    response_payload = service.score_accounts_batch(["acct-atlas-01"])

    assert response_payload["result_persistence"] == {
        "status": "degraded",
        "reason": "batch_score_write_failed",
        "run_id": response_payload["run_id"],
    }
