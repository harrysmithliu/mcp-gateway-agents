from pydantic import BaseModel, Field


class RiskBatchScoreRequest(BaseModel):
    account_ids: list[str] = Field(..., min_length=1)
