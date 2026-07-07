from pydantic import BaseModel, Field


class UpdateAlertStatusRequest(BaseModel):
    status: str = Field(..., min_length=1)
