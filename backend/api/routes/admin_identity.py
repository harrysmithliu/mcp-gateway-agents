from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_admin_identity_service
from backend.api.schemas.admin_identity import (
    AdminUserResponse,
    CreateAdminUserRequest,
    ReplaceAdminUserRolesRequest,
    UpdateAdminUserActivityRequest,
)
from backend.auth.dependencies import require_principal_roles
from backend.auth.models import IdentityPrincipal
from backend.auth.rbac import Role
from backend.services.admin_identity import (
    AdminIdentityError,
    AdminIdentityService,
    ManagedUser,
    ManagedUserNotFoundError,
)


router = APIRouter(prefix="/admin/users", tags=["admin-identity"])


@router.get("", response_model=list[AdminUserResponse])
def list_admin_users(
    principal: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.ADMIN)),
    ],
    identity_service: Annotated[
        AdminIdentityService,
        Depends(get_admin_identity_service),
    ],
) -> list[AdminUserResponse]:
    _ = principal
    return [_build_response(user) for user in identity_service.list_users()]


@router.post("", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    request: CreateAdminUserRequest,
    principal: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.ADMIN)),
    ],
    identity_service: Annotated[
        AdminIdentityService,
        Depends(get_admin_identity_service),
    ],
) -> AdminUserResponse:
    try:
        user = identity_service.create_user(
            username=request.username,
            display_name=request.display_name,
            password=request.password,
            roles=request.roles,
            actor_user_id=principal.user_id,
        )
    except AdminIdentityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_response(user)


@router.put("/{user_id}/roles", response_model=AdminUserResponse)
def replace_admin_user_roles(
    user_id: int,
    request: ReplaceAdminUserRolesRequest,
    principal: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.ADMIN)),
    ],
    identity_service: Annotated[
        AdminIdentityService,
        Depends(get_admin_identity_service),
    ],
) -> AdminUserResponse:
    try:
        user = identity_service.replace_roles(
            user_id=user_id,
            roles=request.roles,
            actor_user_id=principal.user_id,
        )
    except ManagedUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AdminIdentityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_response(user)


@router.patch("/{user_id}/activity", response_model=AdminUserResponse)
def update_admin_user_activity(
    user_id: int,
    request: UpdateAdminUserActivityRequest,
    principal: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.ADMIN)),
    ],
    identity_service: Annotated[
        AdminIdentityService,
        Depends(get_admin_identity_service),
    ],
) -> AdminUserResponse:
    try:
        user = identity_service.set_user_active(
            user_id=user_id,
            is_active=request.is_active,
            actor_user_id=principal.user_id,
        )
    except ManagedUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AdminIdentityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_response(user)


def _build_response(user: ManagedUser) -> AdminUserResponse:
    return AdminUserResponse(
        user_id=user.user_id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=list(user.roles),
    )
