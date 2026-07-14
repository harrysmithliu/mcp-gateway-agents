CREATE TABLE IF NOT EXISTS knowledge.ingestion_runs (
    run_id UUID PRIMARY KEY,
    requested_by_user_id BIGINT REFERENCES iam.users(user_id) ON DELETE SET NULL,
    run_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    source_count INTEGER NOT NULL DEFAULT 0,
    document_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    embedding_count INTEGER NOT NULL DEFAULT 0,
    embedding_provider TEXT,
    embedding_model_name TEXT,
    vector_dimensions INTEGER,
    error_type TEXT,
    error_summary TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ingestion_runs_status_check
        CHECK (status IN ('running', 'succeeded', 'failed')),
    CONSTRAINT ingestion_runs_mode_check
        CHECK (run_mode IN ('manual_refresh'))
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_created_at
    ON knowledge.ingestion_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status
    ON knowledge.ingestion_runs (status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ingestion_runs_single_running
    ON knowledge.ingestion_runs (status)
    WHERE status = 'running';

CREATE TABLE IF NOT EXISTS knowledge.ingestion_run_sources (
    run_id UUID NOT NULL REFERENCES knowledge.ingestion_runs(run_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    source_path TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    byte_size BIGINT NOT NULL,
    content_type TEXT NOT NULL,
    access_level TEXT NOT NULL,
    jurisdiction TEXT,
    tags JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_id, source_id)
);

CREATE INDEX IF NOT EXISTS idx_ingestion_run_sources_source_id
    ON knowledge.ingestion_run_sources (source_id);
