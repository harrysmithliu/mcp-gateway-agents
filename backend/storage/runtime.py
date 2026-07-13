from dataclasses import dataclass

from backend.storage.db import DatabaseClient, DatabaseConfig
from backend.storage.repositories.audit_events import AuditEventRepository
from backend.storage.repositories.chat_messages import ChatMessageRepository
from backend.storage.repositories.chat_sessions import ChatSessionRepository
from backend.storage.repositories.chunk_embeddings import ChunkEmbeddingRepository
from backend.storage.repositories.knowledge_chunks import KnowledgeChunkRepository
from backend.storage.repositories.knowledge_documents import KnowledgeDocumentRepository
from backend.storage.repositories.knowledge_search import KnowledgeSearchRepository
from backend.storage.repositories.risk_alerts import RiskAlertRepository
from backend.storage.repositories.risk_alert_status_events import (
    RiskAlertStatusEventRepository,
)
from backend.storage.repositories.risk_batch_scores import RiskBatchScoreRepository
from backend.storage.repositories.tool_call_logs import ToolCallLogRepository
from backend.storage.settings import Settings


@dataclass(slots=True)
class StorageBundle:
    """App-level relational persistence bundle for operational write paths."""

    config: DatabaseConfig
    database_client: DatabaseClient
    chat_session_repository: ChatSessionRepository
    chat_message_repository: ChatMessageRepository
    tool_call_log_repository: ToolCallLogRepository
    audit_event_repository: AuditEventRepository
    risk_alert_repository: RiskAlertRepository
    risk_alert_status_event_repository: RiskAlertStatusEventRepository
    risk_batch_score_repository: RiskBatchScoreRepository
    knowledge_document_repository: KnowledgeDocumentRepository
    knowledge_chunk_repository: KnowledgeChunkRepository
    chunk_embedding_repository: ChunkEmbeddingRepository
    knowledge_search_repository: KnowledgeSearchRepository


def build_storage_bundle(settings: Settings) -> StorageBundle:
    config = DatabaseConfig(database_url=settings.database_url)
    database_client = DatabaseClient(config=config)
    return StorageBundle(
        config=config,
        database_client=database_client,
        chat_session_repository=ChatSessionRepository(executor=database_client),
        chat_message_repository=ChatMessageRepository(executor=database_client),
        tool_call_log_repository=ToolCallLogRepository(executor=database_client),
        audit_event_repository=AuditEventRepository(executor=database_client),
        risk_alert_repository=RiskAlertRepository(executor=database_client),
        risk_alert_status_event_repository=RiskAlertStatusEventRepository(
            executor=database_client
        ),
        risk_batch_score_repository=RiskBatchScoreRepository(executor=database_client),
        knowledge_document_repository=KnowledgeDocumentRepository(executor=database_client),
        knowledge_chunk_repository=KnowledgeChunkRepository(executor=database_client),
        chunk_embedding_repository=ChunkEmbeddingRepository(executor=database_client),
        knowledge_search_repository=KnowledgeSearchRepository(executor=database_client),
    )
