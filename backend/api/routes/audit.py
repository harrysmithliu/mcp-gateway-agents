from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_audit_service
from backend.auth.rbac import DemoUser, Role, require_roles
from backend.services.audit import AuditService

router = APIRouter(tags=["audit"])


@router.get("/audit/recent-events")
def get_recent_audit_events(
    user: Annotated[
        DemoUser,
        Depends(require_roles(Role.SUPERVISOR, Role.ADMIN)),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    limit: int = Query(default=10, ge=1, le=100),
    event_type: str | None = None,
) -> dict[str, object]:
    return audit_service.list_recent_events(limit=limit, event_type=event_type)
