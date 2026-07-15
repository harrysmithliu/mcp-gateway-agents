import logging
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from backend.retrieval.contracts import (
    RetrievalQuery,
    RetrievalChunk,
    RetrievalCitation,
    RetrievalContext,
    RetrievalMetadata,
    RetrievalRuntimeStatus,
)
from backend.retrieval.embedding_provider import EmbeddingProvider
from backend.retrieval.ingestion_models import EmbeddingConfig
from backend.retrieval.query import embed_query
from backend.storage.models import KnowledgeSearchRecord
from backend.storage.repositories.knowledge_search import KnowledgeSearchRepository

if TYPE_CHECKING:
    from backend.agent.ports import ToolGatewayPort


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievalService:
    """Orchestrates query embedding, vector search, and citation mapping."""

    vector_backend: str = "postgresql_pgvector"
    embedding_config: EmbeddingConfig | None = None
    embedding_provider: EmbeddingProvider | None = None
    knowledge_search_repository: KnowledgeSearchRepository | None = None
    enabled: bool = True
    runtime_error: str | None = None
    minimum_similarity: float = 0.15

    def describe(self) -> str:
        return "Retrieval service backed by configured embeddings and PostgreSQL/pgvector."

    def runtime_status(self) -> RetrievalRuntimeStatus:
        """Return the public, non-secret state of this retrieval runtime."""

        if not self.enabled:
            return RetrievalRuntimeStatus(
                state="disabled",
                enabled=False,
                vector_backend=self.vector_backend,
                provider=self._provider_name,
                model_name=self._model_name,
                vector_dimensions=self._vector_dimensions,
                reason="disabled_by_configuration",
            )

        if self.runtime_error is not None:
            return RetrievalRuntimeStatus(
                state="unavailable",
                enabled=True,
                vector_backend=self.vector_backend,
                provider=self._provider_name,
                model_name=self._model_name,
                vector_dimensions=self._vector_dimensions,
                reason=self.runtime_error,
            )

        if (
            self.embedding_config is None
            or self.embedding_provider is None
            or self.knowledge_search_repository is None
        ):
            return RetrievalRuntimeStatus(
                state="unavailable",
                enabled=True,
                vector_backend=self.vector_backend,
                provider=self._provider_name,
                model_name=self._model_name,
                vector_dimensions=self._vector_dimensions,
                reason="runtime_not_configured",
            )

        return RetrievalRuntimeStatus(
            state="ready",
            enabled=True,
            vector_backend=self.vector_backend,
            provider=self._provider_name,
            model_name=self._model_name,
            vector_dimensions=self._vector_dimensions,
        )

    def retrieve(self, query: RetrievalQuery) -> RetrievalContext:
        """Run one configured vector search and map rows into RAG contracts."""

        started_at = perf_counter()
        if not self.enabled:
            return self._build_runtime_disabled_result(query)

        if self.runtime_error is not None:
            return self._build_runtime_unavailable_result(query)

        if (
            self.embedding_config is None
            or self.embedding_provider is None
            or self.knowledge_search_repository is None
        ):
            raise RuntimeError("RetrievalService runtime is not configured.")

        try:
            query_embedding = embed_query(
                query=query,
                embedding_config=self.embedding_config,
                embedding_provider=self.embedding_provider,
            )
            records = self.knowledge_search_repository.search_similar_chunks(
                query=query,
                query_embedding=query_embedding,
            )
            records = [
                record
                for record in records
                if record.similarity_score >= self.minimum_similarity
            ]
        except Exception as exc:
            logger.exception(
                "Knowledge retrieval failed",
                extra={
                    "retrieval_source": "postgresql_pgvector",
                    "top_k": query.top_k,
                },
            )
            return RetrievalContext(
                rag_enabled=False,
                retrieval_source="postgresql_pgvector",
                metadata=RetrievalMetadata(
                    top_k=query.top_k,
                    filters=self._build_filter_payload(query),
                    status="failed",
                    latency_ms=self._build_latency_ms(started_at),
                    failure_reason=type(exc).__name__,
                ),
            )

        return RetrievalContext(
            rag_enabled=bool(records),
            retrieval_source=self.vector_backend,
            retrieved_chunks=[self._build_retrieval_chunk(record) for record in records],
            citations=[self._build_retrieval_citation(record) for record in records],
            metadata=RetrievalMetadata(
                provider=query_embedding.provider,
                model_name=query_embedding.model_name,
                vector_dimensions=query_embedding.vector_dimensions,
                top_k=query.top_k,
                result_count=len(records),
                filters=self._build_filter_payload(query),
                status="completed" if records else "empty",
                latency_ms=self._build_latency_ms(started_at),
            ),
        )

    def _build_runtime_disabled_result(self, query: RetrievalQuery) -> RetrievalContext:
        return RetrievalContext(
            rag_enabled=False,
            retrieval_source=self.vector_backend,
            metadata=RetrievalMetadata(
                provider=self._provider_name,
                model_name=self._model_name,
                vector_dimensions=self._vector_dimensions,
                top_k=query.top_k,
                filters=self._build_filter_payload(query),
                status="disabled",
                failure_reason="disabled_by_configuration",
            ),
        )

    def _build_runtime_unavailable_result(
        self,
        query: RetrievalQuery,
    ) -> RetrievalContext:
        return RetrievalContext(
            rag_enabled=False,
            retrieval_source=self.vector_backend,
            metadata=RetrievalMetadata(
                provider=self._provider_name,
                model_name=self._model_name,
                vector_dimensions=self._vector_dimensions,
                top_k=query.top_k,
                filters=self._build_filter_payload(query),
                status="unavailable",
                failure_reason=self.runtime_error,
            ),
        )

    @property
    def _provider_name(self) -> str | None:
        return self.embedding_config.provider if self.embedding_config else None

    @property
    def _model_name(self) -> str | None:
        return self.embedding_config.model_name if self.embedding_config else None

    @property
    def _vector_dimensions(self) -> int | None:
        return self.embedding_config.vector_dimensions if self.embedding_config else None

    @staticmethod
    def _build_latency_ms(started_at: float) -> int:
        return max(0, round((perf_counter() - started_at) * 1000))

    @staticmethod
    def _build_filter_payload(query: RetrievalQuery) -> dict[str, object]:
        filters: dict[str, object] = {}
        access_levels = query.effective_access_levels
        if len(access_levels) == 1:
            filters["access_level"] = access_levels[0]
        elif access_levels:
            filters["allowed_access_levels"] = list(access_levels)
        if query.jurisdiction is not None:
            filters["jurisdiction"] = query.jurisdiction
        if query.tags:
            filters["tags"] = list(query.tags)
        return filters

    @staticmethod
    def _build_retrieval_chunk(record: KnowledgeSearchRecord) -> RetrievalChunk:
        return RetrievalChunk(
            document_id=record.document_id,
            title=record.title,
            summary=record.chunk_text,
            chunk_id=record.chunk_id,
            chunk_index=record.chunk_index,
            source_path=record.source_path,
            score=record.similarity_score,
            metadata=record.chunk_metadata,
        )

    @staticmethod
    def _build_retrieval_citation(record: KnowledgeSearchRecord) -> RetrievalCitation:
        return RetrievalCitation(
            document_id=record.document_id,
            title=record.title,
            chunk_id=record.chunk_id,
            chunk_index=record.chunk_index,
            source_path=record.source_path,
            score=record.similarity_score,
            excerpt=record.chunk_text,
        )

    def build_context(
        self,
        normalized_text: str,
        tool_gateway: "ToolGatewayPort",
        limit: int = 2,
    ) -> RetrievalContext:
        matched_records = tool_gateway.preview_knowledge_matches(
            query_text=normalized_text,
            limit=limit,
        )
        if not matched_records:
            return RetrievalContext(
                rag_enabled=False,
                retrieval_source="knowledge_preview",
            )

        return RetrievalContext(
            rag_enabled=True,
            retrieval_source="knowledge_preview",
            retrieved_chunks=[
                RetrievalChunk(
                    document_id=match["document_id"],
                    title=match["title"],
                    summary=match["summary"],
                    matched_terms=list(match["matched_terms"]),
                )
                for match in matched_records
            ],
            citations=[
                RetrievalCitation(
                    document_id=match["document_id"],
                    title=match["title"],
                )
                for match in matched_records
            ],
        )
