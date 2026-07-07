from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import (
    get_account_domain_service,
    get_account_investigation_service,
)
from backend.api.schemas.accounts import AccountInvestigationResponse, AccountSearchRequest
from backend.auth.rbac import DemoUser, Role, require_roles
from backend.services.accounts import AccountDomainService
from backend.services.account_investigation import AccountInvestigationService

router = APIRouter(tags=["accounts"])


@router.post("/accounts/search")
def search_accounts(
    request: AccountSearchRequest,
    user: Annotated[
        DemoUser,
        Depends(
            require_roles(
                Role.ANALYST,
                Role.RISK_OPERATOR,
                Role.SUPERVISOR,
                Role.ADMIN,
            )
        ),
    ],
    account_domain_service: Annotated[
        AccountDomainService, Depends(get_account_domain_service)
    ],
) -> dict[str, object]:
    return account_domain_service.search_accounts(
        query_text=request.query,
        limit=request.limit,
    )


@router.get("/accounts/{account_id}/overview")
def get_account_overview(
    account_id: str,
    user: Annotated[
        DemoUser,
        Depends(
            require_roles(
                Role.ANALYST,
                Role.RISK_OPERATOR,
                Role.SUPERVISOR,
                Role.ADMIN,
            )
        ),
    ],
    account_domain_service: Annotated[
        AccountDomainService, Depends(get_account_domain_service)
    ],
) -> dict[str, object]:
    overview = account_domain_service.get_account_overview(account_id)
    if overview is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return overview


@router.get("/accounts/{account_id}/activity-summary")
def get_account_activity_summary(
    account_id: str,
    user: Annotated[
        DemoUser,
        Depends(
            require_roles(
                Role.ANALYST,
                Role.RISK_OPERATOR,
                Role.SUPERVISOR,
                Role.ADMIN,
            )
        ),
    ],
    account_domain_service: Annotated[
        AccountDomainService, Depends(get_account_domain_service)
    ],
) -> dict[str, object]:
    summary = account_domain_service.get_recent_activity_summary(account_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return summary


@router.get(
    "/accounts/{account_id}/investigation",
    response_model=AccountInvestigationResponse,
)
def get_account_investigation(
    account_id: str,
    user: Annotated[
        DemoUser,
        Depends(
            require_roles(
                Role.ANALYST,
                Role.RISK_OPERATOR,
                Role.SUPERVISOR,
                Role.ADMIN,
            )
        ),
    ],
    account_investigation_service: Annotated[
        AccountInvestigationService, Depends(get_account_investigation_service)
    ],
) -> AccountInvestigationResponse:
    investigation = account_investigation_service.get_account_investigation(account_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountInvestigationResponse(**investigation)
