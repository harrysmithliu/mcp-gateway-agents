from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.dependencies import get_knowledge_ingestion_service
from backend.api.schemas.knowledge_ingestion import (
    KnowledgeIngestionRunDetailResponse,
    KnowledgeIngestionRunListResponse,
)
from backend.auth.dependencies import require_principal_roles
from backend.auth.models import IdentityPrincipal
from backend.auth.rbac import Role
from backend.services.knowledge_ingestion import (
    KnowledgeIngestionAlreadyRunningError,
    KnowledgeIngestionService,
)

router = APIRouter(tags=["knowledge-admin"])

AdminPrincipal = Annotated[
    IdentityPrincipal,
    Depends(require_principal_roles(Role.ADMIN)),
]


@router.post(
    "/admin/knowledge/ingestion-runs",
    response_model=KnowledgeIngestionRunDetailResponse,
    status_code=status.HTTP_200_OK,
)
def trigger_knowledge_ingestion(
    principal: AdminPrincipal,
    ingestion_service: Annotated[
        KnowledgeIngestionService,
        Depends(get_knowledge_ingestion_service),
    ],
) -> dict[str, object]:
    try:
        return ingestion_service.run_manual_refresh(
            actor_user_id=principal.user.user_id,
        )
    except KnowledgeIngestionAlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/admin/knowledge/ingestion-runs",
    response_model=KnowledgeIngestionRunListResponse,
)
def list_knowledge_ingestion_runs(
    principal: AdminPrincipal,
    ingestion_service: Annotated[
        KnowledgeIngestionService,
        Depends(get_knowledge_ingestion_service),
    ],
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, object]:
    _ = principal
    return ingestion_service.list_recent_runs(limit=limit)


@router.get(
    "/admin/knowledge/ingestion-runs/{run_id}",
    response_model=KnowledgeIngestionRunDetailResponse,
)
def get_knowledge_ingestion_run(
    run_id: str,
    principal: AdminPrincipal,
    ingestion_service: Annotated[
        KnowledgeIngestionService,
        Depends(get_knowledge_ingestion_service),
    ],
) -> dict[str, object]:
    _ = principal
    result = ingestion_service.get_run_detail(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    return result
