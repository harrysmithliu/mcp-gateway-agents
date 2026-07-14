from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from backend.retrieval.ingestion_manifest import (
    DEFAULT_INGESTION_DOCUMENTS,
    PROJECT_ROOT,
)
from backend.retrieval.ingestion_models import KnowledgeSourceDocument
from backend.retrieval.persistence import (
    RetrievalPersistenceService,
    build_retrieval_persistence_service,
    run_default_retrieval_persistence_with_runtime,
)
from backend.storage.models import (
    AuditEventRecord,
    KnowledgeIngestionRunRecord,
    KnowledgeIngestionSourceRecord,
)
from backend.storage.runtime import StorageBundle
from backend.storage.settings import Settings


class KnowledgeIngestionAlreadyRunningError(RuntimeError):
    """Raised when an administrator starts a second ingestion run."""


@dataclass(slots=True)
class KnowledgeIngestionService:
    storage_bundle: StorageBundle
    settings: Settings
    retrieval_persistence_service: RetrievalPersistenceService
    source_documents: tuple[KnowledgeSourceDocument, ...] = DEFAULT_INGESTION_DOCUMENTS

    def run_manual_refresh(self, actor_user_id: int | None) -> dict[str, object]:
        repository = self.storage_bundle.knowledge_ingestion_run_repository
        if repository.has_running_run():
            raise KnowledgeIngestionAlreadyRunningError(
                "A knowledge ingestion run is already running."
            )

        run_id = str(uuid4())
        repository.create_run(
            KnowledgeIngestionRunRecord(
                run_id=run_id,
                requested_by_user_id=actor_user_id,
                run_mode="manual_refresh",
                status="running",
            )
        )

        try:
            source_records = self.build_source_manifest(run_id)
            for source_record in source_records:
                repository.create_source(source_record)

            run_result = run_default_retrieval_persistence_with_runtime(
                service=self.retrieval_persistence_service,
                settings=self.settings,
            )
            persistence_result = run_result.persistence_result
            vector_dimensions = self._resolve_vector_dimensions(run_result)
            repository.mark_succeeded(
                run_id=run_id,
                source_count=len(source_records),
                document_count=persistence_result.document_count,
                chunk_count=persistence_result.chunk_count,
                embedding_count=persistence_result.embedding_count,
                embedding_provider=self.settings.embedding_provider,
                embedding_model_name=run_result.batch_result.embedding_model_name,
                vector_dimensions=vector_dimensions,
            )
            self._write_audit_event(
                actor_user_id=actor_user_id,
                event_type="knowledge_ingestion_succeeded",
                event_summary="Knowledge ingestion run completed.",
                event_payload={
                    "run_id": run_id,
                    "run_mode": "manual_refresh",
                    "source_count": len(source_records),
                    "document_count": persistence_result.document_count,
                    "chunk_count": persistence_result.chunk_count,
                    "embedding_count": persistence_result.embedding_count,
                },
            )
        except Exception as exc:
            error_type = type(exc).__name__
            error_summary = self._safe_error_summary(exc)
            repository.mark_failed(
                run_id=run_id,
                error_type=error_type,
                error_summary=error_summary,
            )
            self._write_audit_event(
                actor_user_id=actor_user_id,
                event_type="knowledge_ingestion_failed",
                event_summary="Knowledge ingestion run failed.",
                event_payload={
                    "run_id": run_id,
                    "run_mode": "manual_refresh",
                    "error_type": error_type,
                    "error_summary": error_summary,
                },
            )

        return self.get_run_detail(run_id) or {"run_id": run_id}

    def build_source_manifest(
        self,
        run_id: str,
    ) -> list[KnowledgeIngestionSourceRecord]:
        return [
            self._build_source_record(run_id=run_id, document=document)
            for document in self.source_documents
        ]

    def list_recent_runs(self, limit: int = 20) -> dict[str, object]:
        try:
            runs = self.storage_bundle.knowledge_ingestion_run_repository.list_recent_runs(
                limit=limit
            )
            return {
                "query_status": "completed",
                "limit": limit,
                "runs": [self._normalize_run_row(run) for run in runs],
            }
        except Exception:
            return {"query_status": "degraded", "limit": limit, "runs": []}

    def get_run_detail(self, run_id: str) -> dict[str, object] | None:
        run = self.storage_bundle.knowledge_ingestion_run_repository.get_run(run_id)
        if run is None:
            return None
        return {
            "query_status": "completed",
            "run": self._normalize_run_row(run),
            "sources": [
                self._normalize_source_row(source)
                for source in self.storage_bundle.knowledge_ingestion_run_repository.list_sources(
                    run_id
                )
            ],
        }

    @staticmethod
    def _normalize_run_row(row: dict[str, object]) -> dict[str, object]:
        normalized = dict(row)
        if normalized.get("run_id") is not None:
            normalized["run_id"] = str(normalized["run_id"])
        return normalized

    @staticmethod
    def _normalize_source_row(row: dict[str, object]) -> dict[str, object]:
        normalized = dict(row)
        if normalized.get("run_id") is not None:
            normalized["run_id"] = str(normalized["run_id"])
        return normalized

    def _build_source_record(
        self,
        run_id: str,
        document: KnowledgeSourceDocument,
    ) -> KnowledgeIngestionSourceRecord:
        source_path = Path(document.file_path)
        content = source_path.read_bytes()
        try:
            display_path = str(source_path.relative_to(PROJECT_ROOT))
        except ValueError:
            display_path = source_path.name
        return KnowledgeIngestionSourceRecord(
            run_id=run_id,
            source_id=document.source_id,
            title=document.title,
            source_path=display_path,
            checksum_sha256=sha256(content).hexdigest(),
            byte_size=len(content),
            content_type=document.content_type,
            access_level=document.access_level,
            jurisdiction=document.jurisdiction,
            tags=list(document.tags),
        )

    @staticmethod
    def _resolve_vector_dimensions(run_result) -> int | None:
        if not run_result.batch_result.vector_records:
            return None
        return len(run_result.batch_result.vector_records[0].embedding)

    def _write_audit_event(
        self,
        actor_user_id: int | None,
        event_type: str,
        event_summary: str,
        event_payload: dict[str, object],
    ) -> None:
        try:
            self.storage_bundle.audit_event_repository.create_audit_event(
                AuditEventRecord(
                    event_id=str(uuid4()),
                    actor_user_id=actor_user_id,
                    event_type=event_type,
                    event_summary=event_summary,
                    event_payload=event_payload,
                )
            )
        except Exception:
            return

    @staticmethod
    def _safe_error_summary(exc: Exception) -> str:
        detail = str(exc).strip().replace("\n", " ")
        if not detail:
            return "Knowledge ingestion failed."
        return detail[:500]


def build_knowledge_ingestion_service(
    storage_bundle: StorageBundle,
    settings: Settings,
) -> KnowledgeIngestionService:
    return KnowledgeIngestionService(
        storage_bundle=storage_bundle,
        settings=settings,
        retrieval_persistence_service=build_retrieval_persistence_service(
            storage_bundle
        ),
    )
