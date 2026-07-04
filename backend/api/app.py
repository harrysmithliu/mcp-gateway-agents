from fastapi import FastAPI

from backend.api.routes.chat import router as chat_router
from backend.api.routes.health import router as health_router
from backend.storage.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        summary="Skeleton for the MCP gateway agent platform.",
    )
    app.include_router(chat_router)
    app.include_router(health_router)
    return app


app = create_app()
