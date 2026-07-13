from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.dependencies import get_auth_service
from backend.auth.models import IdentityPrincipal, IdentityUser
from backend.auth.rbac import DEFAULT_DEMO_USERS
from backend.auth.service import AuthService, AuthenticationError
from backend.storage.settings import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> IdentityPrincipal:
    if get_settings().auth_mode == "demo":
        username = request.headers.get("x-demo-user", "analyst_demo")
        demo_user = DEFAULT_DEMO_USERS.get(username)
        if demo_user is None:
            raise HTTPException(status_code=401, detail="Unknown demo user")
        demo_user_ids = {
            "analyst_demo": 1,
            "risk_operator_demo": 2,
            "supervisor_demo": 3,
            "admin_demo": 4,
        }
        return IdentityPrincipal(
            user=IdentityUser(
                user_id=demo_user_ids[username],
                username=demo_user.username,
                display_name=demo_user.display_name,
                is_active=True,
            ),
            roles=(demo_user.role.value,),
            auth_session_id=f"demo-{username}",
            browser_session_id="demo-browser",
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return auth_service.principal_from_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_principal_roles(*allowed_roles: str):
    allowed = {str(role) for role in allowed_roles}

    def dependency(
        principal: Annotated[IdentityPrincipal, Depends(get_current_principal)],
    ) -> IdentityPrincipal:
        if not allowed.intersection(principal.roles):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return principal

    return dependency
