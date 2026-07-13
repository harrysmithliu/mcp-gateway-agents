from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_auth_service
from backend.api.schemas.auth import AuthUserResponse, LoginRequest, LoginResponse
from backend.auth.dependencies import get_current_principal
from backend.auth.models import IdentityPrincipal
from backend.auth.rbac import list_demo_users
from backend.auth.service import AuthService, AuthenticationError

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    try:
        result = auth_service.authenticate(
            username=request.username,
            password=request.password,
            browser_session_id=request.browser_session_id,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return LoginResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
        auth_session_id=result.session.session.auth_session_id,
        user=AuthUserResponse(
            user_id=result.session.user.user_id,
            username=result.session.user.username,
            display_name=result.session.user.display_name,
            roles=list(result.session.roles),
        ),
    )


@router.get("/auth/me", response_model=AuthUserResponse)
def get_current_user(
    principal: Annotated[IdentityPrincipal, Depends(get_current_principal)],
) -> AuthUserResponse:
    return AuthUserResponse(
        user_id=principal.user_id,
        username=principal.user.username,
        display_name=principal.user.display_name,
        roles=list(principal.roles),
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    principal: Annotated[IdentityPrincipal, Depends(get_current_principal)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    auth_service.logout(principal)


@router.get("/auth/demo-users")
def get_demo_users() -> dict[str, object]:
    return {
        "default_user": "analyst_demo",
        "users": list_demo_users(),
    }
