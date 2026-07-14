from pydantic import BaseModel


class RetrievalRuntimeResponse(BaseModel):
    state: str
    enabled: bool
    vector_backend: str
    provider: str | None = None
    model_name: str | None = None
    vector_dimensions: int | None = None
    reason: str | None = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    retrieval: RetrievalRuntimeResponse
