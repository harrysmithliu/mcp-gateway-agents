from dataclasses import dataclass

from backend.retrieval.contracts import QueryEmbedding, RetrievalQuery
from backend.storage.db import SQLStatement
from backend.storage.models import KnowledgeSearchRecord
from backend.storage.repositories.base import StatementExecutor
from backend.storage.repositories.chunk_embeddings import serialize_embedding_vector


@dataclass(slots=True)
class KnowledgeSearchRepository:
    """Reads ranked knowledge chunks from PostgreSQL/pgvector."""

    executor: StatementExecutor

    def search_similar_chunks(
        self,
        query: RetrievalQuery,
        query_embedding: QueryEmbedding,
    ) -> list[KnowledgeSearchRecord]:
        where_clauses = [
            "e.embedding_model_name = %(embedding_model_name)s",
            "e.embedding_provider = %(embedding_provider)s",
            "e.vector_dimensions = %(vector_dimensions)s",
        ]
        params: dict[str, object] = {
            "query_embedding": serialize_embedding_vector(query_embedding.vector),
            "embedding_model_name": query_embedding.model_name,
            "embedding_provider": query_embedding.provider,
            "vector_dimensions": query_embedding.vector_dimensions,
            "top_k": query.top_k,
        }

        if query.access_level is not None:
            where_clauses.append("d.access_level = %(access_level)s")
            params["access_level"] = query.access_level
        if query.jurisdiction is not None:
            where_clauses.append("d.jurisdiction = %(jurisdiction)s")
            params["jurisdiction"] = query.jurisdiction
        if query.tags:
            where_clauses.append("d.tags @> CAST(%(tags)s AS jsonb)")
            params["tags"] = list(query.tags)

        statement = SQLStatement(
            sql=(
                "SELECT c.chunk_id, c.document_id, d.title, d.file_path AS source_path, "
                "c.chunk_index, c.chunk_text, c.chunk_metadata, "
                "1 - (e.embedding <=> CAST(%(query_embedding)s AS vector)) "
                "AS similarity_score "
                "FROM knowledge.chunk_embeddings AS e "
                "JOIN knowledge.knowledge_chunks AS c ON c.chunk_id = e.chunk_id "
                "JOIN knowledge.knowledge_documents AS d ON d.document_id = c.document_id "
                f"WHERE {' AND '.join(where_clauses)} "
                "ORDER BY e.embedding <=> CAST(%(query_embedding)s AS vector) "
                "LIMIT %(top_k)s"
            ),
            params=params,
        )
        rows = self.executor.fetch_all(statement)
        return [self._build_search_record(row) for row in rows]

    @staticmethod
    def _build_search_record(row: dict[str, object]) -> KnowledgeSearchRecord:
        chunk_metadata = row.get("chunk_metadata")
        return KnowledgeSearchRecord(
            chunk_id=str(row["chunk_id"]),
            document_id=str(row["document_id"]),
            title=str(row["title"]),
            source_path=str(row["source_path"]),
            chunk_index=int(row["chunk_index"]),
            chunk_text=str(row["chunk_text"]),
            chunk_metadata=(
                dict(chunk_metadata) if isinstance(chunk_metadata, dict) else {}
            ),
            similarity_score=float(row["similarity_score"]),
        )
