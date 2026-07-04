from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.agent.service import AgentService

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    user_role: str = Field(..., min_length=1)
    message_text: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply_text: str
    tool_names: list[str]
    evidence: list[str]
    actions: list[str]


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    agent_service = AgentService()
    agent_response = agent_service.handle_chat(
        user_role=request.user_role,
        message_text=request.message_text,
    )
    return ChatResponse(
        reply_text=agent_response.reply_text,
        tool_names=agent_response.tool_names,
        evidence=agent_response.evidence,
        actions=agent_response.actions,
    )
