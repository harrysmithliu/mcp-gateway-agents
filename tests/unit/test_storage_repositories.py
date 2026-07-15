import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import SQLStatement
from backend.auth.models import AuthSessionRecord
from backend.storage.models import (
    AuditEventRecord,
    ChatMessageRecord,
    ChatSessionRecord,
    ChunkEmbeddingRecord,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    KnowledgeIngestionRunRecord,
    KnowledgeIngestionSourceRecord,
    RiskAlertRecord,
    RiskAlertStatusEventRecord,
    RiskBatchScoreResultRecord,
    RiskBatchScoreRunRecord,
    ToolCallLogRecord,
)
from backend.storage.repositories.audit_events import AuditEventRepository
from backend.storage.repositories.chat_messages import ChatMessageRepository
from backend.storage.repositories.chat_sessions import ChatSessionRepository
from backend.storage.repositories.chunk_embeddings import ChunkEmbeddingRepository
from backend.storage.repositories.knowledge_chunks import KnowledgeChunkRepository
from backend.storage.repositories.knowledge_documents import KnowledgeDocumentRepository
from backend.storage.repositories.knowledge_ingestion_runs import (
    KnowledgeIngestionRunRepository,
)
from backend.storage.repositories.knowledge_search import KnowledgeSearchRepository
from backend.storage.repositories.risk_alerts import RiskAlertRepository
from backend.storage.repositories.risk_alert_status_events import (
    RiskAlertStatusEventRepository,
)
from backend.storage.repositories.risk_batch_scores import RiskBatchScoreRepository
from backend.storage.repositories.tool_call_logs import ToolCallLogRepository
from backend.storage.repositories.identity import IdentityRepository


class FakeExecutor:
    def __init__(self) -> None:
        self.statements: list[SQLStatement] = []

    def execute(self, statement: SQLStatement) -> None:
        self.statements.append(statement)


class FetchFakeExecutor(FakeExecutor):
    def __init__(self, rows: list[dict[str, object]]) -> None:
        super().__init__()
        self.rows = rows

    def fetch_all(self, statement: SQLStatement) -> list[dict[str, object]]:
        self.statements.append(statement)
        return self.rows


class SequentialFetchFakeExecutor(FakeExecutor):
    def __init__(self, responses: list[list[dict[str, object]]]) -> None:
        super().__init__()
        self.responses = responses

    def fetch_all(self, statement: SQLStatement) -> list[dict[str, object]]:
        self.statements.append(statement)
        return self.responses.pop(0)


def test_identity_repository_builds_auth_session_insert_statement() -> None:
    executor = FakeExecutor()
    repository = IdentityRepository(executor=executor)
    record = AuthSessionRecord(
        auth_session_id="session-1",
        user_id=101,
        browser_session_id="browser-1",
        token_jti="jti-1",
        expires_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    statement = repository.create_auth_session(record)

    assert "INSERT INTO iam.auth_sessions" in statement.sql
    assert statement.params["user_id"] == 101
    assert statement.params["token_jti"] == "jti-1"
    assert executor.statements == [statement]


def test_identity_repository_builds_active_session_query() -> None:
    executor = SequentialFetchFakeExecutor(
        [
            [
                {
                    "auth_session_id": "session-1",
                    "user_id": 101,
                    "browser_session_id": "browser-1",
                    "token_jti": "jti-1",
                    "expires_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "username": "analyst_demo",
                    "display_name": "Analyst Demo",
                    "is_active": True,
                }
            ],
            [{"role_name": "analyst"}],
        ]
    )
    repository = IdentityRepository(executor=executor)

    session = repository.get_active_auth_session("session-1", "jti-1")

    assert session is not None
    assert session.user.username == "analyst_demo"
    assert "expires_at > NOW()" in executor.statements[0].sql


def test_chat_session_repository_builds_insert_statement() -> None:
    executor = FakeExecutor()
    repository = ChatSessionRepository(executor=executor)

    statement = repository.create_session(
        ChatSessionRecord(
            session_id="session-1",
            user_id=None,
            session_title="Risk review",
        )
    )

    assert "INSERT INTO convo.chat_sessions" in statement.sql
    assert "ON CONFLICT (session_id) DO NOTHING" in statement.sql
    assert statement.params == {
        "session_id": "session-1",
        "user_id": None,
        "session_title": "Risk review",
    }
    assert executor.statements == [statement]


def test_chat_session_repository_builds_ownership_lookup_and_claim_statements() -> None:
    executor = FetchFakeExecutor([{"session_id": "session-1", "user_id": 101}])
    repository = ChatSessionRepository(executor=executor)

    session = repository.get_session("session-1")
    claim_statement = repository.claim_session("session-1", 101)

    assert session == {"session_id": "session-1", "user_id": 101}
    assert "user_id IS NULL" in claim_statement.sql


def test_chat_message_repository_builds_insert_statement() -> None:
    executor = FakeExecutor()
    repository = ChatMessageRepository(executor=executor)

    statement = repository.append_message(
        ChatMessageRecord(
            message_id="message-1",
            session_id="session-1",
            sender_type="user",
            message_text="Check the borrower concentration risk.",
        )
    )

    assert "INSERT INTO convo.chat_messages" in statement.sql
    assert statement.params == {
        "message_id": "message-1",
        "session_id": "session-1",
        "sender_type": "user",
        "message_text": "Check the borrower concentration risk.",
    }
    assert executor.statements == [statement]


def test_tool_call_log_repository_builds_insert_statement() -> None:
    executor = FakeExecutor()
    repository = ToolCallLogRepository(executor=executor)

    statement = repository.create_tool_call_log(
        ToolCallLogRecord(
            tool_call_id="tool-call-1",
            session_id="session-1",
            message_id="message-1",
            actor_user_id=101,
            tool_namespace="knowledge",
            tool_name="knowledge.search",
            call_status="completed",
            request_payload={"query": "verafin"},
            response_payload={"matches": 3},
            error_message=None,
            latency_ms=42,
        )
    )

    assert "INSERT INTO audit.tool_call_logs" in statement.sql
    assert statement.params == {
        "tool_call_id": "tool-call-1",
        "session_id": "session-1",
        "message_id": "message-1",
        "actor_user_id": 101,
        "tool_namespace": "knowledge",
        "tool_name": "knowledge.search",
        "call_status": "completed",
        "request_payload": {"query": "verafin"},
        "response_payload": {"matches": 3},
        "error_message": None,
        "latency_ms": 42,
    }
    assert executor.statements == [statement]


def test_audit_event_repository_builds_insert_statement() -> None:
    executor = FakeExecutor()
    repository = AuditEventRepository(executor=executor)

    statement = repository.create_audit_event(
        AuditEventRecord(
            event_id="event-1",
            actor_user_id=101,
            event_type="tool_invocation",
            event_summary="Knowledge search executed.",
            event_payload={"tool_name": "knowledge.search"},
        )
    )

    assert "INSERT INTO audit.audit_events" in statement.sql
    assert statement.params == {
        "event_id": "event-1",
        "actor_user_id": 101,
        "event_type": "tool_invocation",
        "event_summary": "Knowledge search executed.",
        "event_payload": {"tool_name": "knowledge.search"},
    }
    assert executor.statements == [statement]


def test_risk_alert_repository_builds_insert_statement() -> None:
    executor = FakeExecutor()
    repository = RiskAlertRepository(executor=executor)

    statement = repository.create_risk_alert(
        RiskAlertRecord(
            alert_id="alert-1",
            session_id="session-1",
            message_id="message-1",
            actor_user_id=101,
            alert_type="manual_review",
            severity="medium",
            status="open",
            summary="Escalate wallet review.",
            details={"reason": "threshold exceeded"},
        )
    )

    assert "INSERT INTO risk.risk_alerts" in statement.sql
    assert statement.params == {
        "alert_id": "alert-1",
        "session_id": "session-1",
        "message_id": "message-1",
        "actor_user_id": 101,
        "alert_type": "manual_review",
        "severity": "medium",
        "status": "open",
        "summary": "Escalate wallet review.",
        "details": {"reason": "threshold exceeded"},
    }
    assert executor.statements == [statement]


def test_knowledge_document_repository_builds_upsert_statement() -> None:
    executor = FakeExecutor()
    repository = KnowledgeDocumentRepository(executor=executor)

    statement = repository.create_document(
        KnowledgeDocumentRecord(
            document_id="kb-policy-trading-surveillance",
            title="Trading Surveillance Policy",
            content_type="text/markdown",
            access_level="internal",
            file_path="/tmp/policy.md",
            tags=["policy", "trading"],
            jurisdiction="global",
        )
    )

    assert "INSERT INTO knowledge.knowledge_documents" in statement.sql
    assert "ON CONFLICT (document_id) DO UPDATE SET" in statement.sql
    assert statement.params == {
        "document_id": "kb-policy-trading-surveillance",
        "title": "Trading Surveillance Policy",
        "content_type": "text/markdown",
        "access_level": "internal",
        "jurisdiction": "global",
        "file_path": "/tmp/policy.md",
        "tags": ["policy", "trading"],
        "content_checksum_sha256": None,
        "index_fingerprint": None,
    }
    assert executor.statements == [statement]


def test_knowledge_chunk_repository_builds_upsert_statement() -> None:
    executor = FakeExecutor()
    repository = KnowledgeChunkRepository(executor=executor)

    statement = repository.create_chunk(
        KnowledgeChunkRecord(
            chunk_id="kb-policy-trading-surveillance-chunk-0",
            document_id="kb-policy-trading-surveillance",
            chunk_index=0,
            chunk_text="Escalate suspicious trading activity for analyst review.",
            chunk_metadata={"content_type": "text/markdown"},
        )
    )

    assert "INSERT INTO knowledge.knowledge_chunks" in statement.sql
    assert "ON CONFLICT (chunk_id) DO UPDATE SET" in statement.sql
    assert statement.params == {
        "chunk_id": "kb-policy-trading-surveillance-chunk-0",
        "document_id": "kb-policy-trading-surveillance",
        "chunk_index": 0,
        "chunk_text": "Escalate suspicious trading activity for analyst review.",
        "chunk_metadata": {"content_type": "text/markdown"},
    }
    assert executor.statements == [statement]


def test_chunk_embedding_repository_builds_upsert_statement() -> None:
    executor = FakeExecutor()
    repository = ChunkEmbeddingRepository(executor=executor)

    statement = repository.create_embedding(
        ChunkEmbeddingRecord(
            chunk_id="kb-policy-trading-surveillance-chunk-0",
            embedding_model_name="mock-embedding-model",
            embedding_provider="mock",
            vector_dimensions=4,
            embedding=[0.1, 0.2, 0.3, 0.4],
        )
    )

    assert "INSERT INTO knowledge.chunk_embeddings" in statement.sql
    assert "CAST(%(embedding)s AS vector)" in statement.sql
    assert "ON CONFLICT (chunk_id) DO UPDATE SET" in statement.sql
    assert statement.params == {
        "chunk_id": "kb-policy-trading-surveillance-chunk-0",
        "embedding_model_name": "mock-embedding-model",
        "embedding_provider": "mock",
        "vector_dimensions": 4,
        "embedding": "[0.10000000000000001,0.20000000000000001,0.29999999999999999,0.40000000000000002]",
    }
    assert executor.statements == [statement]


def test_knowledge_search_repository_builds_pgvector_similarity_query() -> None:
    executor = FetchFakeExecutor(
        rows=[
            {
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "title": "Trading Policy",
                "source_path": "data/knowledge_sources/trading.md",
                "chunk_index": 2,
                "chunk_text": "Escalate suspicious activity.",
                "chunk_metadata": {"topic": "surveillance"},
                "similarity_score": 0.91,
            }
        ]
    )
    repository = KnowledgeSearchRepository(executor=executor)
    from backend.retrieval.contracts import QueryEmbedding, RetrievalQuery

    records = repository.search_similar_chunks(
        query=RetrievalQuery(
            text="suspicious activity",
            top_k=3,
            access_level="internal",
            jurisdiction="global",
            tags=("policy",),
        ),
        query_embedding=QueryEmbedding(
            vector=[0.1, 0.2, 0.3, 0.4],
            provider="local_sentence_transformer",
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            vector_dimensions=4,
        ),
    )

    statement = executor.statements[0]
    assert "FROM knowledge.chunk_embeddings AS e" in statement.sql
    assert "JOIN knowledge.knowledge_chunks AS c" in statement.sql
    assert "JOIN knowledge.knowledge_documents AS d" in statement.sql
    assert "e.embedding <=> CAST(%(query_embedding)s AS vector)" in statement.sql
    assert "ORDER BY e.embedding <=>" in statement.sql
    assert "LIMIT %(top_k)s" in statement.sql
    assert "d.access_level = %(access_level)s" in statement.sql
    assert "d.jurisdiction = %(jurisdiction)s" in statement.sql
    assert "d.tags @> CAST(%(tags)s AS jsonb)" in statement.sql
    assert statement.params["top_k"] == 3
    assert statement.params["embedding_provider"] == "local_sentence_transformer"
    assert statement.params["embedding_model_name"] == (
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    assert records[0].chunk_id == "chunk-1"
    assert records[0].similarity_score == 0.91
    assert records[0].chunk_metadata == {"topic": "surveillance"}


def test_knowledge_search_repository_builds_parameterized_hierarchical_scope() -> None:
    executor = FetchFakeExecutor(rows=[])
    repository = KnowledgeSearchRepository(executor=executor)
    from backend.retrieval.contracts import QueryEmbedding, RetrievalQuery

    repository.search_similar_chunks(
        query=RetrievalQuery(
            text="restricted policy",
            allowed_access_levels=("internal", "restricted"),
        ),
        query_embedding=QueryEmbedding(
            vector=[0.1, 0.2, 0.3, 0.4],
            provider="local_sentence_transformer",
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            vector_dimensions=4,
        ),
    )

    statement = executor.statements[0]
    assert "d.access_level IN (%(allowed_access_level_0)s, %(allowed_access_level_1)s)" in statement.sql
    assert "allowed_access_levels" not in statement.params
    assert statement.params["allowed_access_level_0"] == "internal"
    assert statement.params["allowed_access_level_1"] == "restricted"


def test_knowledge_ingestion_run_repository_builds_lifecycle_and_manifest_statements() -> None:
    executor = SequentialFetchFakeExecutor(
        [
            [{"run_id": "run-1", "status": "running"}],
            [{"run_id": "run-1", "source_id": "kb-policy"}],
        ]
    )
    repository = KnowledgeIngestionRunRepository(executor=executor)

    create_statement = repository.create_run(
        KnowledgeIngestionRunRecord(
            run_id="run-1",
            requested_by_user_id=4,
            run_mode="manual_refresh",
            status="running",
        )
    )
    source_statement = repository.create_source(
        KnowledgeIngestionSourceRecord(
            run_id="run-1",
            source_id="kb-policy",
            title="Trading Policy",
            source_path="data/knowledge_sources/trading.md",
            checksum_sha256="a" * 64,
            byte_size=128,
            content_type="text/markdown",
            access_level="internal",
            tags=["policy"],
        )
    )
    success_statement = repository.mark_succeeded(
        run_id="run-1",
        source_count=1,
        document_count=1,
        chunk_count=2,
        embedding_count=2,
        embedding_provider="local_sentence_transformer",
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        vector_dimensions=384,
    )
    failure_statement = repository.mark_failed(
        run_id="run-1",
        error_type="RuntimeError",
        error_summary="embedding provider unavailable",
    )
    run = repository.get_run("run-1")
    sources = repository.list_sources("run-1")

    assert "INSERT INTO knowledge.ingestion_runs" in create_statement.sql
    assert create_statement.params["status"] == "running"
    assert "INSERT INTO knowledge.ingestion_run_sources" in source_statement.sql
    assert source_statement.params["checksum_sha256"] == "a" * 64
    assert "status = 'succeeded'" in success_statement.sql
    assert success_statement.params["vector_dimensions"] == 384
    assert "status = 'failed'" in failure_statement.sql
    assert run == {"run_id": "run-1", "status": "running"}
    assert sources == [{"run_id": "run-1", "source_id": "kb-policy"}]


def test_risk_batch_score_repository_builds_run_and_result_statements() -> None:
    executor = FakeExecutor()
    repository = RiskBatchScoreRepository(executor=executor)

    run_statement = repository.create_run(
        RiskBatchScoreRunRecord(
            run_id="run-1",
            requested_account_count=2,
            scored_account_count=2,
            missing_account_count=0,
            highest_risk_score=82,
            average_risk_score=71.5,
            risk_level_counts={"high": 1, "medium": 1, "low": 0},
            actor_user_id=101,
        )
    )
    result_statement = repository.create_result(
        RiskBatchScoreResultRecord(
            result_id="result-1",
            run_id="run-1",
            account_id="acct-atlas-01",
            profile_id="profile-atlas-01",
            risk_score=82,
            risk_level="high",
            review_status="pending",
            exposure_usd=250000,
            alert_count_30d=3,
            risk_flags=["rapid_withdrawal"],
        )
    )

    assert "INSERT INTO risk.batch_score_runs" in run_statement.sql
    assert "INSERT INTO risk.batch_score_results" in result_statement.sql
    assert run_statement.params["risk_level_counts"] == {
        "high": 1,
        "medium": 1,
        "low": 0,
    }
    assert result_statement.params["risk_flags"] == ["rapid_withdrawal"]
    assert executor.statements == [run_statement, result_statement]


def test_risk_batch_score_repository_reads_run_and_results() -> None:
    executor = FetchFakeExecutor(
        rows=[
            {
                "run_id": "run-1",
                "account_id": "acct-atlas-01",
                "risk_score": 82,
            }
        ]
    )
    repository = RiskBatchScoreRepository(executor=executor)

    run = repository.get_run("run-1")
    results = repository.list_results("run-1")

    assert run == executor.rows[0]
    assert results == executor.rows[0:1]
    assert "FROM risk.batch_score_runs" in executor.statements[0].sql
    assert "FROM risk.batch_score_results" in executor.statements[1].sql


def test_risk_alert_status_event_repository_builds_history_statement() -> None:
    executor = FakeExecutor()
    repository = RiskAlertStatusEventRepository(executor=executor)

    statement = repository.create_event(
        RiskAlertStatusEventRecord(
            event_id="status-event-1",
            alert_id="alert-1",
            previous_status="open",
            next_status="acknowledged",
            reason="Analyst accepted review.",
            details={"source": "ops_api"},
        )
    )

    assert "INSERT INTO risk.risk_alert_status_events" in statement.sql
    assert statement.params["previous_status"] == "open"
    assert statement.params["next_status"] == "acknowledged"
    assert executor.statements == [statement]
