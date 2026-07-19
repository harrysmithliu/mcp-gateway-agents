CREATE TABLE IF NOT EXISTS iam.runtime_switches (
    switch_key TEXT PRIMARY KEY,
    is_enabled BOOLEAN NOT NULL,
    updated_by_user_id BIGINT REFERENCES iam.users(user_id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO iam.runtime_switches (switch_key, is_enabled)
VALUES
    ('maintenance_mode', FALSE),
    ('response_cache_enabled', TRUE),
    ('retrieval_enabled', TRUE)
ON CONFLICT (switch_key) DO NOTHING;
