from pydantic import BaseModel


class RuntimeSwitchResponse(BaseModel):
    key: str
    is_enabled: bool
    default_enabled: bool
    description: str


class UpdateRuntimeSwitchRequest(BaseModel):
    is_enabled: bool
