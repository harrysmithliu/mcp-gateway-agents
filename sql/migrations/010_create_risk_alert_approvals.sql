CREATE TABLE IF NOT EXISTS risk.risk_alert_approvals (
    approval_id UUID PRIMARY KEY,
    alert_id UUID NOT NULL REFERENCES risk.risk_alerts(alert_id) ON DELETE CASCADE,
    requested_by_user_id BIGINT REFERENCES iam.users(user_id) ON DELETE SET NULL,
    decided_by_user_id BIGINT REFERENCES iam.users(user_id) ON DELETE SET NULL,
    approval_status TEXT NOT NULL CHECK (approval_status IN ('requested', 'approved', 'rejected')),
    request_reason TEXT NOT NULL,
    decision_reason TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_risk_alert_approvals_alert_id
    ON risk.risk_alert_approvals (alert_id, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_risk_alert_approvals_status
    ON risk.risk_alert_approvals (approval_status, requested_at DESC);
