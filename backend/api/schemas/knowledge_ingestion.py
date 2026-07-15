from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeIngestionSourceResponse(BaseModel):
    run_id: str
    source_id: str
    title: str
    source_path: str
    checksum_sha256: str
    byte_size: int
    content_type: str
    access_level: str
    jurisdiction: str | None = None
    tags: list[str] = Field(default_factory=list)
    index_fingerprint: str | None = None
    created_at: datetime | None = None


class KnowledgeIngestionRunResponse(BaseModel):
    run_id: str
    requested_by_user_id: int | None = None
    run_mode: str
    status: str
    source_count: int = 0
    document_count: int = 0
    chunk_count: int = 0
    embedding_count: int = 0
    embedding_provider: str | None = None
    embedding_model_name: str | None = None
    vector_dimensions: int | None = None
    error_type: str | None = None
    error_summary: str | None = None
    change_summary: dict[str, object] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class KnowledgeIngestionRunListResponse(BaseModel):
    query_status: str
    limit: int
    runs: list[KnowledgeIngestionRunResponse]


class KnowledgeIngestionRunDetailResponse(BaseModel):
    query_status: str
    run: KnowledgeIngestionRunResponse
    sources: list[KnowledgeIngestionSourceResponse]
