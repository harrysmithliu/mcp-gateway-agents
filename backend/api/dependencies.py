from dataclasses import dataclass
from pathlib import Path

from fastapi import Request

from backend.agent.service import AgentService
from backend.auth.passwords import PasswordService
from backend.auth.service import AuthService
from backend.auth.tokens import JWTTokenService
from backend.diagnostics.readiness import RuntimeReadinessService
from backend.diagnostics.admin_status import AdminRuntimeStatusService
from backend.guardrails.policy import GuardrailPolicy
from backend.agent.ports import ToolGatewayPort
from backend.cache.policy import CacheEligibilityPolicy
from backend.cache.redis import RedisResponseCache
from backend.mcp_gateway.registry import build_default_registry
from backend.mcp_gateway.sdk_adapter import MCPSDKAdapter
from backend.mcp_gateway.transport import build_mcp_transport_router
from backend.retrieval.runtime import build_retrieval_service
from backend.retrieval.service import RetrievalService
from backend.services.audit import AuditService
from backend.services.account_investigation import AccountInvestigationService
from backend.services.accounts import AccountDomainService
from backend.services.knowledge import KnowledgeService
from backend.services.knowledge_ingestion import (
    KnowledgeIngestionService,
    build_knowledge_ingestion_service,
)
from backend.services.operations import OperationsService
from backend.services.ops_workflow import OpsWorkflowService
from backend.services.risk import RiskService
from backend.services.risk_batch import RiskBatchScoreService
from backend.storage.chat_persistence import ChatPersistenceCoordinator
from backend.storage.redis_chat_context import RedisChatContextStore
from backend.storage.runtime import StorageBundle, build_storage_bundle
from backend.storage.settings import get_settings
from backend.services.trade import TradeService


@dataclass(slots=True)
class ApplicationContainer:
    """App-level dependency container for the current runnable backend."""

    agent_service: AgentService
    tool_registry: ToolGatewayPort
    retrieval_service: RetrievalService
    guardrail_policy: GuardrailPolicy
    account_domain_service: AccountDomainService
    account_investigation_service: AccountInvestigationService
    audit_service: AuditService
    ops_workflow_service: OpsWorkflowService
    mcp_sdk_adapter: MCPSDKAdapter
    knowledge_service: KnowledgeService
    knowledge_ingestion_service: KnowledgeIngestionService
    risk_service: RiskService
    risk_batch_score_service: RiskBatchScoreService
    trade_service: TradeService
    operations_service: OperationsService
    storage_bundle: StorageBundle
    chat_persistence_coordinator: ChatPersistenceCoordinator
    redis_chat_context_store: RedisChatContextStore
    auth_service: AuthService
    runtime_readiness_service: RuntimeReadinessService
    admin_runtime_status_service: AdminRuntimeStatusService


def build_application_container() -> ApplicationContainer:
    settings = get_settings()
    guardrail_policy = GuardrailPolicy()
    account_domain_service = AccountDomainService()
    knowledge_service = KnowledgeService()
    risk_service = RiskService()
    trade_service = TradeService()
    operations_service = OperationsService()
    storage_bundle = build_storage_bundle(settings)
    auth_service = AuthService(
        identity_store=storage_bundle.identity_repository,
        password_service=PasswordService(),
        token_service=JWTTokenService(
            secret=settings.auth_jwt_secret or "local-development-secret-change-me-32-bytes",
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
            ttl_seconds=settings.auth_access_token_ttl_seconds,
        ),
        allow_multiple_identities=settings.auth_allow_multiple_identities,
    )
    retrieval_service = build_retrieval_service(
        settings=settings,
        knowledge_search_repository=storage_bundle.knowledge_search_repository,
    )
    knowledge_ingestion_service = build_knowledge_ingestion_service(
        storage_bundle=storage_bundle,
        settings=settings,
    )
    redis_chat_context_store = RedisChatContextStore(redis_url=settings.redis_url)
    cache_policy = CacheEligibilityPolicy(
        ttl_seconds=settings.response_cache_ttl_seconds,
        key_prefix=settings.response_cache_key_prefix,
    )
    response_cache = (
        RedisResponseCache(redis_url=settings.redis_url)
        if settings.response_cache_enabled
        else None
    )
    chat_persistence_coordinator = ChatPersistenceCoordinator(
        storage_bundle=storage_bundle,
        redis_chat_context_store=redis_chat_context_store,
    )
    risk_batch_score_service = RiskBatchScoreService(
        risk_service=risk_service,
        risk_batch_score_repository=storage_bundle.risk_batch_score_repository,
        database_client=storage_bundle.database_client,
    )
    base_registry = build_default_registry(
        knowledge_service=knowledge_service,
        risk_service=risk_service,
        trade_service=trade_service,
        operations_service=operations_service,
        retrieval_service=retrieval_service,
    )
    tool_gateway = build_mcp_transport_router(
        registry=base_registry,
        transport_mode=settings.mcp_transport_mode,
        server_runtime=settings.mcp_server_runtime,
    )
    mcp_sdk_adapter = MCPSDKAdapter(
        transport_mode=settings.mcp_transport_mode,
        server_runtime=settings.mcp_server_runtime,
    )
    runtime_readiness_service = RuntimeReadinessService(
        settings=settings,
        database_client=storage_bundle.database_client,
        redis_chat_context_store=redis_chat_context_store,
        retrieval_service=retrieval_service,
        response_cache_enabled=settings.response_cache_enabled,
        response_cache_ttl_seconds=settings.response_cache_ttl_seconds,
        response_cache_key_prefix=settings.response_cache_key_prefix,
        tool_registry=tool_gateway,
    )
    admin_runtime_status_service = AdminRuntimeStatusService(
        settings=settings,
        database_client=storage_bundle.database_client,
        readiness_service=runtime_readiness_service,
        mcp_sdk_adapter=mcp_sdk_adapter,
        project_root=Path(__file__).resolve().parents[2],
    )
    return ApplicationContainer(
        agent_service=AgentService(
            retrieval_service=retrieval_service,
            guardrail_policy=guardrail_policy,
            chat_persistence_coordinator=chat_persistence_coordinator,
            redis_chat_context_store=redis_chat_context_store,
            response_cache=response_cache,
            cache_policy=cache_policy,
            response_cache_enabled=settings.response_cache_enabled,
        ),
        tool_registry=tool_gateway,
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
        mcp_sdk_adapter=mcp_sdk_adapter,
        knowledge_service=knowledge_service,
        knowledge_ingestion_service=knowledge_ingestion_service,
        risk_service=risk_service,
        risk_batch_score_service=risk_batch_score_service,
        trade_service=trade_service,
        operations_service=operations_service,
        storage_bundle=storage_bundle,
        chat_persistence_coordinator=chat_persistence_coordinator,
        redis_chat_context_store=redis_chat_context_store,
        auth_service=auth_service,
        runtime_readiness_service=runtime_readiness_service,
        admin_runtime_status_service=admin_runtime_status_service,
    )


def get_application_container(request: Request) -> ApplicationContainer:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("Application container is not initialized.")
    return container


def get_agent_service(request: Request) -> AgentService:
    return get_application_container(request).agent_service


def get_tool_registry(request: Request) -> ToolGatewayPort:
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


def get_auth_service(request: Request) -> AuthService:
    return get_application_container(request).auth_service


def get_knowledge_ingestion_service(request: Request) -> KnowledgeIngestionService:
    return get_application_container(request).knowledge_ingestion_service


def get_admin_runtime_status_service(request: Request) -> AdminRuntimeStatusService:
    return get_application_container(request).admin_runtime_status_service
