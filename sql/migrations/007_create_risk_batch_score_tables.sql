CREATE TABLE IF NOT EXISTS risk.batch_score_runs (
    run_id UUID PRIMARY KEY,
    actor_user_id BIGINT REFERENCES iam.users(user_id) ON DELETE SET NULL,
    requested_account_count INTEGER NOT NULL,
    scored_account_count INTEGER NOT NULL,
    missing_account_count INTEGER NOT NULL,
    highest_risk_score INTEGER NOT NULL,
    average_risk_score NUMERIC(8, 2) NOT NULL,
    risk_level_counts JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk.batch_score_results (
    result_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES risk.batch_score_runs(run_id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    review_status TEXT NOT NULL,
    exposure_usd BIGINT NOT NULL,
    alert_count_30d INTEGER NOT NULL,
    risk_flags JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, account_id)
);

CREATE INDEX IF NOT EXISTS idx_batch_score_runs_actor_user_id
    ON risk.batch_score_runs (actor_user_id);

CREATE INDEX IF NOT EXISTS idx_batch_score_runs_created_at
    ON risk.batch_score_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_batch_score_results_run_id
    ON risk.batch_score_results (run_id);

CREATE INDEX IF NOT EXISTS idx_batch_score_results_account_id
    ON risk.batch_score_results (account_id);
