from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_mcp_sdk_adapter
from backend.mcp_gateway.sdk_adapter import MCPSDKAdapter
from backend.auth.dependencies import require_principal_roles
from backend.auth.models import IdentityPrincipal
from backend.auth.rbac import Role

router = APIRouter(tags=["mcp"])


@router.get("/mcp/sdk-status")
def get_mcp_sdk_status(
    principal: Annotated[
        IdentityPrincipal,
        Depends(require_principal_roles(Role.ADMIN)),
    ],
    mcp_sdk_adapter: Annotated[MCPSDKAdapter, Depends(get_mcp_sdk_adapter)],
) -> dict[str, object]:
    return mcp_sdk_adapter.build_sdk_status()
