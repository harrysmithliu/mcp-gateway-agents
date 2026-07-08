import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import SQLStatement
from backend.storage.models import (
    AuditEventRecord,
    ChatMessageRecord,
    ChatSessionRecord,
    ChunkEmbeddingRecord,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    RiskAlertRecord,
    ToolCallLogRecord,
)
from backend.storage.repositories.audit_events import AuditEventRepository
from backend.storage.repositories.chat_messages import ChatMessageRepository
from backend.storage.repositories.chat_sessions import ChatSessionRepository
from backend.storage.repositories.chunk_embeddings import ChunkEmbeddingRepository
from backend.storage.repositories.knowledge_chunks import KnowledgeChunkRepository
from backend.storage.repositories.knowledge_documents import KnowledgeDocumentRepository
from backend.storage.repositories.risk_alerts import RiskAlertRepository
from backend.storage.repositories.tool_call_logs import ToolCallLogRepository


class FakeExecutor:
    def __init__(self) -> None:
        self.statements: list[SQLStatement] = []

    def execute(self, statement: SQLStatement) -> None:
        self.statements.append(statement)


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
