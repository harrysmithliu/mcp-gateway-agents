from pydantic import BaseModel, Field


class AccountInvestigationResponse(BaseModel):
    account_overview: dict[str, object]
    recent_activity: dict[str, object] | None
    risk_profile: dict[str, object] | None
    trade_metrics: dict[str, object] | None


class AccountSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
