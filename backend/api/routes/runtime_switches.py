from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_runtime_switch_service
from backend.api.schemas.runtime_switches import (
    RuntimeSwitchResponse,
    UpdateRuntimeSwitchRequest,
)
from backend.auth.dependencies import require_principal_roles
from backend.auth.models import IdentityPrincipal
from backend.auth.rbac import Role
from backend.services.runtime_switches import RuntimeSwitchError, RuntimeSwitchService


router = APIRouter(prefix="/admin/runtime-switches", tags=["admin-runtime-switches"])


@router.get("", response_model=list[RuntimeSwitchResponse])
def list_runtime_switches(
    principal: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.ADMIN)),
    ],
    switch_service: Annotated[
        RuntimeSwitchService,
        Depends(get_runtime_switch_service),
    ],
) -> list[RuntimeSwitchResponse]:
    _ = principal
    return [
        RuntimeSwitchResponse(**state.to_payload())
        for state in switch_service.list_switches()
    ]


@router.put("/{switch_key}", response_model=RuntimeSwitchResponse)
def update_runtime_switch(
    switch_key: str,
    request: UpdateRuntimeSwitchRequest,
    principal: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.ADMIN)),
    ],
    switch_service: Annotated[
        RuntimeSwitchService,
        Depends(get_runtime_switch_service),
    ],
) -> RuntimeSwitchResponse:
    try:
        state = switch_service.set_enabled(
            key=switch_key,
            is_enabled=request.is_enabled,
            actor_user_id=principal.user_id,
        )
    except RuntimeSwitchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RuntimeSwitchResponse(**state.to_payload())
