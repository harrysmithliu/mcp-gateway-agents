from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_ops_workflow_service
from backend.api.schemas.ops import UpdateAlertStatusRequest
from backend.auth.rbac import DemoUser, Role, require_roles
from backend.services.ops_workflow import OpsWorkflowService

router = APIRouter(tags=["operations"])


@router.get("/ops/alerts")
def list_recent_alerts(
    user: Annotated[
        DemoUser,
        Depends(require_roles(Role.RISK_OPERATOR, Role.SUPERVISOR, Role.ADMIN)),
    ],
    ops_workflow_service: Annotated[
        OpsWorkflowService, Depends(get_ops_workflow_service)
    ],
    limit: int = Query(default=10, ge=1, le=100),
    status: str | None = None,
) -> dict[str, object]:
    return ops_workflow_service.list_recent_alerts(limit=limit, status=status)


@router.post("/ops/alerts/{alert_id}/status")
def update_alert_status(
    alert_id: str,
    request: UpdateAlertStatusRequest,
    user: Annotated[
        DemoUser,
        Depends(require_roles(Role.SUPERVISOR, Role.ADMIN)),
    ],
    ops_workflow_service: Annotated[
        OpsWorkflowService, Depends(get_ops_workflow_service)
    ],
) -> dict[str, object]:
    return ops_workflow_service.update_alert_status(
        alert_id=alert_id,
        status=request.status,
    )
