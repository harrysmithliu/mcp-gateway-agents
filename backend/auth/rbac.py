from enum import StrEnum


class Role(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    RISK_OPERATOR = "risk_operator"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
    SERVICE_ACCOUNT = "service_account"

