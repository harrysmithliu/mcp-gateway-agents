from typing import Annotated

from fastapi import APIRouter, Depends

from backend.agent.service import AgentService
from backend.agent.ports import ToolGatewayPort
from backend.api.dependencies import get_agent_service, get_tool_registry
from backend.api.mappers import build_chat_command, build_chat_response
from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.auth.dependencies import get_current_principal
from backend.auth.models import IdentityPrincipal
from backend.storage.chat_persistence import ChatSessionAccessError
from fastapi import HTTPException

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    principal: Annotated[IdentityPrincipal, Depends(get_current_principal)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    registry: Annotated[ToolGatewayPort, Depends(get_tool_registry)],
) -> ChatResponse:
    try:
        agent_response = agent_service.handle_command(
            build_chat_command(request, principal),
            registry=registry,
        )
    except ChatSessionAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return build_chat_response(agent_response, registry)
