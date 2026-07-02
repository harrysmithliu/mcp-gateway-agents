INSERT INTO iam.roles (role_name, role_description)
VALUES
    ('analyst', 'Can run analysis and trigger scoring workflows'),
    ('risk_operator', 'Can create alerts and submit action recommendations'),
    ('supervisor', 'Can approve or reject sensitive risk actions'),
    ('admin', 'Can manage system configuration and audit access')
ON CONFLICT (role_name) DO NOTHING;
