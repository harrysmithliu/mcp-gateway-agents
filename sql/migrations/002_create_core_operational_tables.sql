CREATE TABLE IF NOT EXISTS iam.roles (
    role_id BIGSERIAL PRIMARY KEY,
    role_name TEXT NOT NULL UNIQUE,
    role_description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS iam.users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS iam.user_role_bindings (
    user_id BIGINT NOT NULL REFERENCES iam.users(user_id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES iam.roles(role_id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS convo.chat_sessions (
    session_id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES iam.users(user_id),
    session_title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS convo.chat_messages (
    message_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES convo.chat_sessions(session_id) ON DELETE CASCADE,
    sender_type TEXT NOT NULL,
    message_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit.audit_events (
    event_id UUID PRIMARY KEY,
    actor_user_id BIGINT REFERENCES iam.users(user_id),
    event_type TEXT NOT NULL,
    event_summary TEXT NOT NULL,
    event_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit.tool_call_logs (
    tool_call_id UUID PRIMARY KEY,
    session_id UUID REFERENCES convo.chat_sessions(session_id) ON DELETE SET NULL,
    message_id UUID REFERENCES convo.chat_messages(message_id) ON DELETE SET NULL,
    actor_user_id BIGINT REFERENCES iam.users(user_id) ON DELETE SET NULL,
    tool_namespace TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    call_status TEXT NOT NULL,
    request_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    response_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    error_message TEXT,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tool_call_logs_session_id
    ON audit.tool_call_logs (session_id);

CREATE INDEX IF NOT EXISTS idx_tool_call_logs_actor_user_id
    ON audit.tool_call_logs (actor_user_id);

CREATE INDEX IF NOT EXISTS idx_tool_call_logs_tool_name
    ON audit.tool_call_logs (tool_namespace, tool_name);

CREATE INDEX IF NOT EXISTS idx_tool_call_logs_created_at
    ON audit.tool_call_logs (created_at DESC);
