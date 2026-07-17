from pydantic import BaseModel, Field


class RetrievalRuntimeResponse(BaseModel):
    state: str
    enabled: bool
    vector_backend: str
    provider: str | None = None
    model_name: str | None = None
    vector_dimensions: int | None = None
    reason: str | None = None


class ReadinessComponentResponse(BaseModel):
    name: str
    state: str
    reason_code: str
    message: str
    remediation: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class RuntimeReadinessResponse(BaseModel):
    state: str
    components: list[ReadinessComponentResponse]
    config: dict[str, object]


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    retrieval: RetrievalRuntimeResponse
    readiness: RuntimeReadinessResponse
