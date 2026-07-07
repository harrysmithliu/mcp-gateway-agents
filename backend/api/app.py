from fastapi import FastAPI

from backend.api.dependencies import build_application_container
from backend.api.routes.accounts import router as accounts_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.audit import router as audit_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.health import router as health_router
from backend.api.routes.mcp import router as mcp_router
from backend.api.routes.ops import router as ops_router
from backend.api.routes.risk import router as risk_router
from backend.api.routes.trade import router as trade_router
from backend.api.routes.tools import router as tools_router
from backend.storage.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        summary="Skeleton for the MCP gateway agent platform.",
    )
    app.state.container = build_application_container()
    app.include_router(accounts_router)
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(chat_router)
    app.include_router(mcp_router)
    app.include_router(ops_router)
    app.include_router(risk_router)
    app.include_router(trade_router)
    app.include_router(tools_router)
    app.include_router(health_router)
    return app


app = create_app()
