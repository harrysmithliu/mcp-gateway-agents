from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_application_container
from backend.api.schemas.risk import RiskBatchScoreRequest
from backend.auth.rbac import DemoUser, Role, require_roles
from backend.services.risk import RiskService

router = APIRouter(tags=["risk"])


@router.post("/risk/batch-score")
def batch_score_accounts(
    request: RiskBatchScoreRequest,
    user: Annotated[
        DemoUser,
        Depends(require_roles(Role.RISK_OPERATOR, Role.SUPERVISOR, Role.ADMIN)),
    ],
    container: Annotated[object, Depends(get_application_container)],
) -> dict[str, object]:
    risk_service = container.risk_service
    return risk_service.score_accounts_batch(request.account_ids)
