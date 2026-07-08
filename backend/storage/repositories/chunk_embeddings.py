from dataclasses import dataclass

from backend.storage.db import SQLStatement
from backend.storage.models import ChunkEmbeddingRecord
from backend.storage.repositories.base import StatementExecutor


def serialize_embedding_vector(embedding: list[float]) -> str:
    return "[" + ",".join(format(value, ".17g") for value in embedding) + "]"


@dataclass(slots=True)
class ChunkEmbeddingRepository:
    executor: StatementExecutor

    def create_embedding(self, record: ChunkEmbeddingRecord) -> SQLStatement:
        statement = SQLStatement(
            sql=(
                "INSERT INTO knowledge.chunk_embeddings "
                "("
                "chunk_id, embedding_model_name, embedding_provider, "
                "vector_dimensions, embedding"
                ") "
                "VALUES ("
                "%(chunk_id)s, %(embedding_model_name)s, %(embedding_provider)s, "
                "%(vector_dimensions)s, CAST(%(embedding)s AS vector)"
                ") "
                "ON CONFLICT (chunk_id) DO UPDATE SET "
                "embedding_model_name = EXCLUDED.embedding_model_name, "
                "embedding_provider = EXCLUDED.embedding_provider, "
                "vector_dimensions = EXCLUDED.vector_dimensions, "
                "embedding = CAST(%(embedding)s AS vector)"
            ),
            params={
                "chunk_id": record.chunk_id,
                "embedding_model_name": record.embedding_model_name,
                "embedding_provider": record.embedding_provider,
                "vector_dimensions": record.vector_dimensions,
                "embedding": serialize_embedding_vector(record.embedding),
            },
        )
        self.executor.execute(statement)
        return statement
