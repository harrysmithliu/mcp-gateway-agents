ALTER TABLE audit.audit_events
    ADD COLUMN IF NOT EXISTS request_id UUID;

ALTER TABLE audit.tool_call_logs
    ADD COLUMN IF NOT EXISTS request_id UUID;

CREATE INDEX IF NOT EXISTS idx_audit_events_request_id
    ON audit.audit_events (request_id)
    WHERE request_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tool_call_logs_request_id
    ON audit.tool_call_logs (request_id)
    WHERE request_id IS NOT NULL;
