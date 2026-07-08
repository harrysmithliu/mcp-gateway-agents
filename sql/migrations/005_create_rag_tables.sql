CREATE TABLE IF NOT EXISTS knowledge.knowledge_documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content_type TEXT NOT NULL,
    access_level TEXT NOT NULL,
    jurisdiction TEXT,
    file_path TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge.knowledge_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES knowledge.knowledge_documents(document_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document_id
    ON knowledge.knowledge_chunks (document_id);

CREATE TABLE IF NOT EXISTS knowledge.chunk_embeddings (
    chunk_id TEXT PRIMARY KEY REFERENCES knowledge.knowledge_chunks(chunk_id) ON DELETE CASCADE,
    embedding_model_name TEXT NOT NULL,
    embedding_provider TEXT NOT NULL,
    vector_dimensions INTEGER NOT NULL,
    embedding vector(4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_model_name
    ON knowledge.chunk_embeddings (embedding_model_name);

CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_embedding_hnsw
    ON knowledge.chunk_embeddings
    USING hnsw (embedding vector_cosine_ops);
