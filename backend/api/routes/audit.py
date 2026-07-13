from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_audit_service
from backend.auth.dependencies import require_principal_roles
from backend.auth.models import IdentityPrincipal
from backend.auth.rbac import Role
from backend.services.audit import AuditService

router = APIRouter(tags=["audit"])


@router.get("/audit/recent-events")
def get_recent_audit_events(
    user: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.SUPERVISOR, Role.ADMIN)),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    limit: int = Query(default=10, ge=1, le=100),
    event_type: str | None = None,
    session_id: str | None = None,
    actor_user_id: int | None = None,
) -> dict[str, object]:
    return audit_service.list_recent_events(
        limit=limit,
        event_type=event_type,
        session_id=session_id,
        actor_user_id=actor_user_id,
    )


@router.get("/audit/tool-invocations")
def get_recent_tool_invocations(
    user: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.SUPERVISOR, Role.ADMIN)),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    limit: int = Query(default=10, ge=1, le=100),
    session_id: str | None = None,
    tool_name: str | None = None,
    call_status: str | None = None,
) -> dict[str, object]:
    return audit_service.list_tool_invocations(
        limit=limit,
        session_id=session_id,
        tool_name=tool_name,
        call_status=call_status,
    )
