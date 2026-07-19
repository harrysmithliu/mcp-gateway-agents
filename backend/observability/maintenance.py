from fastapi import Request
from fastapi.responses import JSONResponse

from backend.api.dependencies import get_application_container


_EXEMPT_PREFIXES = ("/admin",)
_EXEMPT_PATHS = {"/health", "/auth/login"}


async def enforce_maintenance_mode(request: Request, call_next):
    """Keep health, sign-in, and authenticated admin recovery paths available."""

    switch_service = get_application_container(request).runtime_switch_service
    maintenance_enabled = (
        switch_service.is_enabled("maintenance_mode", False)
        if switch_service is not None
        else False
    )
    if maintenance_enabled and not _is_exempt_path(request.url.path):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Maintenance mode is active. Please try again later.",
            },
        )
    return await call_next(request)


def _is_exempt_path(path: str) -> bool:
    return path in _EXEMPT_PATHS or path.startswith(_EXEMPT_PREFIXES)
