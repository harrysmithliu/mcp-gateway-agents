from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.retrieval.ingestion_models import KnowledgeSourceDocument
from backend.services.knowledge_ingestion import (
    KnowledgeIngestionAlreadyRunningError,
    KnowledgeIngestionService,
)
from backend.storage.settings import Settings


class FakeIngestionRunRepository:
    def __init__(self, running: bool = False) -> None:
        self.running = running
        self.run_records = []
        self.source_records = []
        self.status_updates = []
        self.run_payload = {
            "run_id": "run-1",
            "status": "succeeded",
            "run_mode": "manual_refresh",
        }

    def has_running_run(self) -> bool:
        return self.running

    def create_run(self, record):
        self.run_records.append(record)

    def create_source(self, record):
        self.source_records.append(record)

    def mark_succeeded(self, **kwargs):
        self.status_updates.append(("succeeded", kwargs))

    def mark_failed(self, **kwargs):
        self.status_updates.append(("failed", kwargs))

    def get_run(self, _run_id):
        return self.run_payload

    def list_sources(self, _run_id):
        return [asdict(record) for record in self.source_records]

    def get_latest_succeeded_run(self):
        return None


class FakeAuditRepository:
    def __init__(self) -> None:
        self.records = []

    def create_audit_event(self, record):
        self.records.append(record)


def build_service(tmp_path: Path, running: bool = False):
    source_path = tmp_path / "policy.md"
    source_path.write_text("Escalate suspicious activity.", encoding="utf-8")
    source_document = KnowledgeSourceDocument(
        source_id="source-1",
        title="Policy",
        file_path=str(source_path),
        content_type="text/markdown",
        tags=("policy",),
        access_level="internal",
    )
    run_repository = FakeIngestionRunRepository(running=running)
    audit_repository = FakeAuditRepository()
    storage_bundle = SimpleNamespace(
        knowledge_ingestion_run_repository=run_repository,
        audit_event_repository=audit_repository,
        database_client=object(),
    )
    service = KnowledgeIngestionService(
        storage_bundle=storage_bundle,
        settings=Settings(
            embedding_provider="mock",
            embedding_model_name="mock-model",
            embedding_dimensions=4,
        ),
        retrieval_persistence_service=object(),
        source_documents=(source_document,),
    )
    return service, run_repository, audit_repository


def test_manual_refresh_persists_manifest_and_success_audit(tmp_path, monkeypatch) -> None:
    service, run_repository, audit_repository = build_service(tmp_path)
    monkeypatch.setattr(
        "backend.services.knowledge_ingestion.run_default_retrieval_refresh_with_runtime",
        lambda **_: SimpleNamespace(
            persistence_result=SimpleNamespace(
                document_count=1,
                chunk_count=2,
                embedding_count=2,
                removed_document_count=0,
            ),
            batch_result=SimpleNamespace(
                embedding_model_name="mock-model",
                vector_records=[SimpleNamespace(embedding=[0.1, 0.2, 0.3, 0.4])],
            ),
        ),
    )

    result = service.run_manual_refresh(actor_user_id=4)

    assert result["run"]["status"] == "succeeded"
    assert run_repository.run_records[0].status == "running"
    assert len(run_repository.source_records) == 1
    assert len(run_repository.source_records[0].checksum_sha256) == 64
    assert run_repository.status_updates[0][0] == "succeeded"
    assert audit_repository.records[0].event_type == "knowledge_ingestion_succeeded"


def test_manual_refresh_marks_failed_and_writes_failure_audit(tmp_path, monkeypatch) -> None:
    service, run_repository, audit_repository = build_service(tmp_path)
    monkeypatch.setattr(
        "backend.services.knowledge_ingestion.run_default_retrieval_refresh_with_runtime",
        lambda **_: (_ for _ in ()).throw(RuntimeError("provider unavailable")),
    )

    service.run_manual_refresh(actor_user_id=4)

    assert run_repository.status_updates[0][0] == "failed"
    assert run_repository.status_updates[0][1]["error_type"] == "RuntimeError"
    assert audit_repository.records[0].event_type == "knowledge_ingestion_failed"


def test_manual_refresh_rejects_another_running_run(tmp_path) -> None:
    service, _, _ = build_service(tmp_path, running=True)

    with pytest.raises(KnowledgeIngestionAlreadyRunningError):
        service.run_manual_refresh(actor_user_id=4)
