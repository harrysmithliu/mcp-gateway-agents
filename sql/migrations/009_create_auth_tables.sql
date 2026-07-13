CREATE TABLE IF NOT EXISTS iam.user_credentials (
    user_id BIGINT PRIMARY KEY REFERENCES iam.users(user_id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL,
    password_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS iam.auth_sessions (
    auth_session_id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES iam.users(user_id) ON DELETE CASCADE,
    browser_session_id TEXT NOT NULL,
    token_jti UUID NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id
    ON iam.auth_sessions (user_id);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_browser_session_id
    ON iam.auth_sessions (browser_session_id);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_active_expiry
    ON iam.auth_sessions (expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS iam.api_tokens (
    token_id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES iam.users(user_id) ON DELETE CASCADE,
    token_name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_tokens_user_id
    ON iam.api_tokens (user_id);
