from typing import Annotated

from fastapi import APIRouter, Depends

from backend.agent.service import AgentService
from backend.agent.ports import ToolGatewayPort
from backend.api.dependencies import get_agent_service, get_tool_registry
from backend.api.mappers import build_chat_command, build_chat_response
from backend.api.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    registry: Annotated[ToolGatewayPort, Depends(get_tool_registry)],
) -> ChatResponse:
    agent_response = agent_service.handle_command(
        build_chat_command(request),
        registry=registry,
    )
    return build_chat_response(agent_response, registry)
