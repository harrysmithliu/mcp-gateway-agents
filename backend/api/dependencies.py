from dataclasses import dataclass

from fastapi import Request

from backend.agent.service import AgentService
from backend.guardrails.policy import GuardrailPolicy
from backend.mcp_gateway.registry import ToolRegistry, build_default_registry
from backend.mcp_gateway.sdk_adapter import MCPSDKAdapter
from backend.retrieval.service import RetrievalService
from backend.services.audit import AuditService
from backend.services.account_investigation import AccountInvestigationService
from backend.services.accounts import AccountDomainService
from backend.services.knowledge import KnowledgeService
from backend.services.operations import OperationsService
from backend.services.ops_workflow import OpsWorkflowService
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
    account_domain_service: AccountDomainService
    account_investigation_service: AccountInvestigationService
    audit_service: AuditService
    ops_workflow_service: OpsWorkflowService
    mcp_sdk_adapter: MCPSDKAdapter
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
    account_domain_service = AccountDomainService()
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
        account_domain_service=account_domain_service,
        account_investigation_service=AccountInvestigationService(
            account_domain_service=account_domain_service,
            risk_service=risk_service,
            trade_service=trade_service,
        ),
        audit_service=AuditService(storage_bundle=storage_bundle),
        ops_workflow_service=OpsWorkflowService(storage_bundle=storage_bundle),
        mcp_sdk_adapter=MCPSDKAdapter(),
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


def get_account_investigation_service(request: Request) -> AccountInvestigationService:
    return get_application_container(request).account_investigation_service


def get_account_domain_service(request: Request) -> AccountDomainService:
    return get_application_container(request).account_domain_service


def get_audit_service(request: Request) -> AuditService:
    return get_application_container(request).audit_service


def get_ops_workflow_service(request: Request) -> OpsWorkflowService:
    return get_application_container(request).ops_workflow_service


def get_mcp_sdk_adapter(request: Request) -> MCPSDKAdapter:
    return get_application_container(request).mcp_sdk_adapter
