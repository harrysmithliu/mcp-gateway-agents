CREATE TABLE IF NOT EXISTS risk.risk_alert_status_events (
    event_id UUID PRIMARY KEY,
    alert_id UUID NOT NULL REFERENCES risk.risk_alerts(alert_id) ON DELETE CASCADE,
    actor_user_id BIGINT REFERENCES iam.users(user_id) ON DELETE SET NULL,
    previous_status TEXT NOT NULL,
    next_status TEXT NOT NULL,
    reason TEXT,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_alert_status_events_alert_id
    ON risk.risk_alert_status_events (alert_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_risk_alert_status_events_actor_user_id
    ON risk.risk_alert_status_events (actor_user_id);
