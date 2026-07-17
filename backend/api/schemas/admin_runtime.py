from datetime import datetime

from pydantic import BaseModel, Field


class AdminRuntimeStatusResponse(BaseModel):
    observed_at: datetime
    environment: str
    readiness: dict[str, object]
    runtime_mode: dict[str, object] = Field(default_factory=dict)
    migration: dict[str, object] = Field(default_factory=dict)
    mcp: dict[str, object] = Field(default_factory=dict)
