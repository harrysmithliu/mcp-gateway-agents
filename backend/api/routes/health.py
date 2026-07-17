from fastapi import APIRouter, Request

from backend.api.dependencies import get_application_container
from backend.api.schemas.health import HealthResponse
from backend.storage.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = get_settings()
    container = get_application_container(request)
    retrieval_status = container.retrieval_service.runtime_status()
    readiness_report = container.runtime_readiness_service.check()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
        retrieval=retrieval_status.to_payload(),
        readiness=readiness_report.to_payload(),
    )
