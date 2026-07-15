from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=50)
    jurisdiction: str | None = None
    tags: list[str] = Field(default_factory=list)


class RiskScoreAccountRequest(BaseModel):
    query: str = Field(..., min_length=1)


class TradeQueryMetricsRequest(BaseModel):
    query: str = Field(..., min_length=1)


class OpsCreateAlertOrActionRequest(BaseModel):
    query: str = Field(..., min_length=1)
