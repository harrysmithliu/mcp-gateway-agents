CREATE TABLE IF NOT EXISTS risk.risk_alerts (
    alert_id UUID PRIMARY KEY,
    session_id UUID REFERENCES convo.chat_sessions(session_id) ON DELETE SET NULL,
    message_id UUID REFERENCES convo.chat_messages(message_id) ON DELETE SET NULL,
    actor_user_id BIGINT REFERENCES iam.users(user_id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_alerts_session_id
    ON risk.risk_alerts (session_id);

CREATE INDEX IF NOT EXISTS idx_risk_alerts_actor_user_id
    ON risk.risk_alerts (actor_user_id);

CREATE INDEX IF NOT EXISTS idx_risk_alerts_status
    ON risk.risk_alerts (status);

CREATE INDEX IF NOT EXISTS idx_risk_alerts_created_at
    ON risk.risk_alerts (created_at DESC);
