ALTER TABLE knowledge.knowledge_documents
    ADD COLUMN IF NOT EXISTS content_checksum_sha256 TEXT,
    ADD COLUMN IF NOT EXISTS index_fingerprint TEXT;

ALTER TABLE knowledge.ingestion_run_sources
    ADD COLUMN IF NOT EXISTS index_fingerprint TEXT;

ALTER TABLE knowledge.ingestion_runs
    ADD COLUMN IF NOT EXISTS change_summary JSONB NOT NULL DEFAULT '{}'::JSONB;
