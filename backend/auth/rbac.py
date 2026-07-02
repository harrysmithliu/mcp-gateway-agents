from enum import StrEnum


class Role(StrEnum):
    ANALYST = "analyst"
    RISK_OPERATOR = "risk_operator"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
