INSERT INTO iam.users (username, display_name)
VALUES
    ('analyst_demo', 'Analyst Demo'),
    ('risk_operator_demo', 'Risk Operator Demo'),
    ('supervisor_demo', 'Supervisor Demo'),
    ('admin_demo', 'Admin Demo')
ON CONFLICT (username) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    is_active = TRUE;

INSERT INTO iam.user_role_bindings (user_id, role_id)
SELECT user_record.user_id, role_record.role_id
FROM iam.users user_record
JOIN iam.roles role_record ON role_record.role_name = CASE user_record.username
    WHEN 'analyst_demo' THEN 'analyst'
    WHEN 'risk_operator_demo' THEN 'risk_operator'
    WHEN 'supervisor_demo' THEN 'supervisor'
    WHEN 'admin_demo' THEN 'admin'
END
WHERE user_record.username IN (
    'analyst_demo',
    'risk_operator_demo',
    'supervisor_demo',
    'admin_demo'
)
ON CONFLICT (user_id, role_id) DO NOTHING;

INSERT INTO iam.user_credentials (user_id, password_hash)
SELECT user_id,
       '$argon2id$v=19$m=65536,t=3,p=4$za7QNzSwyT7MFOVHJsJZcQ$cUoyTJkUAZlNv2blUGAplVIjJZG/iW1qreWnDNkYn40'
FROM iam.users
WHERE username IN (
    'analyst_demo',
    'risk_operator_demo',
    'supervisor_demo',
    'admin_demo'
)
ON CONFLICT (user_id) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    password_updated_at = NOW();
