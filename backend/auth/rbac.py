from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, Header, HTTPException


class Role(StrEnum):
    ANALYST = "analyst"
    RISK_OPERATOR = "risk_operator"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class DemoUser:
    user_id: str
    username: str
    display_name: str
    role: Role


DEFAULT_DEMO_USERS = {
    "analyst_demo": DemoUser(
        user_id="demo-user-analyst",
        username="analyst_demo",
        display_name="Analyst Demo",
        role=Role.ANALYST,
    ),
    "risk_operator_demo": DemoUser(
        user_id="demo-user-risk-operator",
        username="risk_operator_demo",
        display_name="Risk Operator Demo",
        role=Role.RISK_OPERATOR,
    ),
    "supervisor_demo": DemoUser(
        user_id="demo-user-supervisor",
        username="supervisor_demo",
        display_name="Supervisor Demo",
        role=Role.SUPERVISOR,
    ),
    "admin_demo": DemoUser(
        user_id="demo-user-admin",
        username="admin_demo",
        display_name="Admin Demo",
        role=Role.ADMIN,
    ),
}


def list_demo_users() -> list[dict[str, str]]:
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role.value,
        }
        for user in DEFAULT_DEMO_USERS.values()
    ]


def get_demo_user(
    x_demo_user: Annotated[str, Header(alias="x-demo-user")] = "analyst_demo",
) -> DemoUser:
    user = DEFAULT_DEMO_USERS.get(x_demo_user)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown demo user")
    return user


def require_roles(*allowed_roles: Role) -> Callable[[DemoUser], DemoUser]:
    def dependency(
        user: Annotated[DemoUser, Depends(get_demo_user)],
    ) -> DemoUser:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return dependency
