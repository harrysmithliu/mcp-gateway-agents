from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message_text: str = Field(..., min_length=1)
    user_role: str = Field(default="analyst", min_length=1)
    session_id: str | None = None

    class RecentMessageRequest(BaseModel):
        role: str = Field(..., min_length=1)
        content: str = Field(..., min_length=1)

    recent_messages: list[RecentMessageRequest] = Field(default_factory=list)


class ChatResponse(BaseModel):
    class CitationResponse(BaseModel):
        document_id: str
        title: str
        chunk_id: str | None = None
        chunk_index: int | None = None
        source_path: str | None = None
        score: float | None = None
        excerpt: str | None = None

    class PlannedToolCallResponse(BaseModel):
        tool_name: str
        domain: str
        description: str

    class ToolInvocationResultResponse(BaseModel):
        tool_name: str
        domain: str
        invocation_status: str
        request_payload: dict[str, object]
        response_payload: dict[str, object]

    class PlannerResultResponse(BaseModel):
        planner_source: str
        planner_mode: str
        model_provider: str | None = None
        model_name: str | None = None
        latency_ms: int
        raw_output_text: str | None = None
        candidate_tool_names: list[str]
        selected_tool_names: list[str]
        used_fallback: bool
        fallback_reason: str | None = None

    session_id: str | None = None
    reply_text: str
    tool_names: list[str]
    planned_tool_calls: list[PlannedToolCallResponse]
    tool_invocation_results: list[ToolInvocationResultResponse]
    evidence: list[str]
    actions: list[str]
    citations: list[CitationResponse] = Field(default_factory=list)
    planner_result: PlannerResultResponse | None = None
