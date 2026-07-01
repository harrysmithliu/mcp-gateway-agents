INSERT INTO iam.roles (role_name, role_description)
VALUES
    ('viewer', 'Read-only dashboard and report access'),
    ('analyst', 'Can run analysis and trigger scoring workflows'),
    ('risk_operator', 'Can create alerts and submit action recommendations'),
    ('supervisor', 'Can approve or reject sensitive risk actions'),
    ('admin', 'Can manage system configuration and audit access'),
    ('service_account', 'System-only role for internal jobs')
ON CONFLICT (role_name) DO NOTHING;

