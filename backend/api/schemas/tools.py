from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)


class RiskScoreAccountRequest(BaseModel):
    query: str = Field(..., min_length=1)


class TradeQueryMetricsRequest(BaseModel):
    query: str = Field(..., min_length=1)


class OpsCreateAlertOrActionRequest(BaseModel):
    query: str = Field(..., min_length=1)
