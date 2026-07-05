from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_role: str = Field(..., min_length=1)
    message_text: str = Field(..., min_length=1)
    session_id: str | None = None

    class RecentMessageRequest(BaseModel):
        role: str = Field(..., min_length=1)
        content: str = Field(..., min_length=1)

    recent_messages: list[RecentMessageRequest] = Field(default_factory=list)


class ChatResponse(BaseModel):
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
        raw_output_text: str | None = None
        candidate_tool_names: list[str]
        selected_tool_names: list[str]
        used_fallback: bool
        fallback_reason: str | None = None

    reply_text: str
    tool_names: list[str]
    planned_tool_calls: list[PlannedToolCallResponse]
    tool_invocation_results: list[ToolInvocationResultResponse]
    evidence: list[str]
    actions: list[str]
    planner_result: PlannerResultResponse | None = None
