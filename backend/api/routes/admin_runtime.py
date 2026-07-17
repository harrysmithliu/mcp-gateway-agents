from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_admin_runtime_status_service
from backend.api.schemas.admin_runtime import AdminRuntimeStatusResponse
from backend.auth.dependencies import require_principal_roles
from backend.auth.models import IdentityPrincipal
from backend.auth.rbac import Role
from backend.diagnostics.admin_status import AdminRuntimeStatusService

router = APIRouter(tags=["admin-runtime"])


@router.get(
    "/admin/runtime-status",
    response_model=AdminRuntimeStatusResponse,
)
def get_admin_runtime_status(
    principal: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.ADMIN)),
    ],
    status_service: Annotated[
        AdminRuntimeStatusService,
        Depends(get_admin_runtime_status_service),
    ],
) -> dict[str, object]:
    _ = principal
    return status_service.build_report().to_payload()
