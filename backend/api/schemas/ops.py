from pydantic import BaseModel, Field


class UpdateAlertStatusRequest(BaseModel):
    status: str = Field(..., min_length=1)


class RequestAlertApprovalRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class DecideAlertApprovalRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    reason: str = Field(..., min_length=1, max_length=1000)
