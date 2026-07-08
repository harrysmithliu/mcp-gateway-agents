import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import DatabaseClient, DatabaseConfig
from backend.storage.runtime import StorageBundle, build_storage_bundle
from backend.storage.settings import Settings


def test_build_storage_bundle_creates_database_backed_repositories() -> None:
    settings = Settings(database_url="postgresql://example")

    storage_bundle = build_storage_bundle(settings)

    assert isinstance(storage_bundle, StorageBundle)
    assert storage_bundle.config == DatabaseConfig(database_url="postgresql://example")
    assert isinstance(storage_bundle.database_client, DatabaseClient)
    assert storage_bundle.chat_session_repository.executor is storage_bundle.database_client
    assert storage_bundle.chat_message_repository.executor is storage_bundle.database_client
    assert storage_bundle.tool_call_log_repository.executor is storage_bundle.database_client
    assert storage_bundle.audit_event_repository.executor is storage_bundle.database_client
    assert storage_bundle.risk_alert_repository.executor is storage_bundle.database_client
    assert storage_bundle.knowledge_document_repository.executor is storage_bundle.database_client
    assert storage_bundle.knowledge_chunk_repository.executor is storage_bundle.database_client
    assert storage_bundle.chunk_embedding_repository.executor is storage_bundle.database_client
