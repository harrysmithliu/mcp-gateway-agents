from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_ops_workflow_service
from backend.api.schemas.ops import (
    DecideAlertApprovalRequest,
    RequestAlertApprovalRequest,
    UpdateAlertStatusRequest,
)
from backend.auth.dependencies import require_principal_roles
from backend.auth.models import IdentityPrincipal
from backend.auth.rbac import Role
from backend.services.ops_workflow import OpsWorkflowService

router = APIRouter(tags=["operations"])


@router.get("/ops/alerts")
def list_recent_alerts(
    user: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.RISK_OPERATOR, Role.SUPERVISOR, Role.ADMIN)),
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
        IdentityPrincipal,
        Depends(
            require_principal_roles(Role.RISK_OPERATOR, Role.SUPERVISOR, Role.ADMIN)
        ),
    ],
    ops_workflow_service: Annotated[
        OpsWorkflowService, Depends(get_ops_workflow_service)
    ],
) -> dict[str, object]:
    if Role.RISK_OPERATOR.value in user.roles and request.status != "acknowledged":
        raise HTTPException(
            status_code=403,
            detail="Risk operators may only acknowledge alerts directly.",
        )
    return ops_workflow_service.update_alert_status(
        alert_id=alert_id,
        status=request.status,
        actor_user_id=user.user_id,
    )


@router.get("/ops/approvals")
def list_alert_approvals(
    user: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.RISK_OPERATOR, Role.SUPERVISOR, Role.ADMIN)),
    ],
    ops_workflow_service: Annotated[
        OpsWorkflowService, Depends(get_ops_workflow_service)
    ],
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, object]:
    return ops_workflow_service.list_recent_approvals(limit=limit)


@router.post("/ops/alerts/{alert_id}/approval")
def request_alert_approval(
    alert_id: str,
    request: RequestAlertApprovalRequest,
    user: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.RISK_OPERATOR, Role.SUPERVISOR, Role.ADMIN)),
    ],
    ops_workflow_service: Annotated[
        OpsWorkflowService, Depends(get_ops_workflow_service)
    ],
) -> dict[str, object]:
    return ops_workflow_service.request_alert_approval(
        alert_id=alert_id,
        reason=request.reason,
        requested_by_user_id=user.user_id,
    )


@router.post("/ops/approvals/{approval_id}/decision")
def decide_alert_approval(
    approval_id: str,
    request: DecideAlertApprovalRequest,
    user: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.SUPERVISOR, Role.ADMIN)),
    ],
    ops_workflow_service: Annotated[
        OpsWorkflowService, Depends(get_ops_workflow_service)
    ],
) -> dict[str, object]:
    return ops_workflow_service.decide_alert_approval(
        approval_id=approval_id,
        decision=request.decision,
        reason=request.reason,
        decided_by_user_id=user.user_id,
    )
