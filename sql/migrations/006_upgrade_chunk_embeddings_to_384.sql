DROP INDEX IF EXISTS idx_chunk_embeddings_embedding_hnsw;

DELETE FROM knowledge.chunk_embeddings;

ALTER TABLE knowledge.chunk_embeddings
    ALTER COLUMN embedding TYPE vector(384);

CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_embedding_hnsw
    ON knowledge.chunk_embeddings
    USING hnsw (embedding vector_cosine_ops);
