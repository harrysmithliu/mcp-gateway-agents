from dataclasses import dataclass

from fastapi import Request

from backend.agent.service import AgentService
from backend.guardrails.policy import GuardrailPolicy
from backend.mcp_gateway.registry import ToolRegistry, build_default_registry
from backend.retrieval.service import RetrievalService
from backend.services.knowledge import KnowledgeService
from backend.services.operations import OperationsService
from backend.services.risk import RiskService
from backend.storage.chat_persistence import ChatPersistenceCoordinator
from backend.storage.redis_chat_context import RedisChatContextStore
from backend.storage.runtime import StorageBundle, build_storage_bundle
from backend.storage.settings import get_settings
from backend.services.trade import TradeService


@dataclass(slots=True)
class ApplicationContainer:
    """App-level dependency container for the current runnable backend."""

    agent_service: AgentService
    tool_registry: ToolRegistry
    retrieval_service: RetrievalService
    guardrail_policy: GuardrailPolicy
    knowledge_service: KnowledgeService
    risk_service: RiskService
    trade_service: TradeService
    operations_service: OperationsService
    storage_bundle: StorageBundle
    chat_persistence_coordinator: ChatPersistenceCoordinator
    redis_chat_context_store: RedisChatContextStore


def build_application_container() -> ApplicationContainer:
    settings = get_settings()
    retrieval_service = RetrievalService()
    guardrail_policy = GuardrailPolicy()
    knowledge_service = KnowledgeService()
    risk_service = RiskService()
    trade_service = TradeService()
    operations_service = OperationsService()
    storage_bundle = build_storage_bundle(settings)
    redis_chat_context_store = RedisChatContextStore(redis_url=settings.redis_url)
    chat_persistence_coordinator = ChatPersistenceCoordinator(
        storage_bundle=storage_bundle,
        redis_chat_context_store=redis_chat_context_store,
    )
    return ApplicationContainer(
        agent_service=AgentService(
            retrieval_service=retrieval_service,
            guardrail_policy=guardrail_policy,
            chat_persistence_coordinator=chat_persistence_coordinator,
            redis_chat_context_store=redis_chat_context_store,
        ),
        tool_registry=build_default_registry(
            knowledge_service=knowledge_service,
            risk_service=risk_service,
            trade_service=trade_service,
            operations_service=operations_service,
        ),
        retrieval_service=retrieval_service,
        guardrail_policy=guardrail_policy,
        knowledge_service=knowledge_service,
        risk_service=risk_service,
        trade_service=trade_service,
        operations_service=operations_service,
        storage_bundle=storage_bundle,
        chat_persistence_coordinator=chat_persistence_coordinator,
        redis_chat_context_store=redis_chat_context_store,
    )


def get_application_container(request: Request) -> ApplicationContainer:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("Application container is not initialized.")
    return container


def get_agent_service(request: Request) -> AgentService:
    return get_application_container(request).agent_service


def get_tool_registry(request: Request) -> ToolRegistry:
    return get_application_container(request).tool_registry
