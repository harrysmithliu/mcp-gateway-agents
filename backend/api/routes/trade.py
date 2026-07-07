from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_application_container
from backend.auth.rbac import DemoUser, Role, require_roles

router = APIRouter(tags=["trade"])


@router.get("/trade/accounts/{account_id}/metrics")
def get_trade_metrics_by_account(
    account_id: str,
    user: Annotated[
        DemoUser,
        Depends(
            require_roles(
                Role.ANALYST,
                Role.RISK_OPERATOR,
                Role.SUPERVISOR,
                Role.ADMIN,
            )
        ),
    ],
    container: Annotated[object, Depends(get_application_container)],
) -> dict[str, object]:
    payload = container.trade_service.get_metrics_by_account(account_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Trade metrics not found")
    return payload
