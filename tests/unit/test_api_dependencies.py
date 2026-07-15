import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.models import AgentResponse, ChatCommand
from backend.api.app import app, create_app
from backend.api.dependencies import ApplicationContainer
from backend.mcp_gateway.registry import MCPToolDefinition, ToolInvocationResult, ToolRegistry
from backend.services.account_investigation import AccountInvestigationService


def test_create_app_initializes_application_container() -> None:
    created_app = create_app()

    assert hasattr(created_app.state, "container")
    assert isinstance(created_app.state.container, ApplicationContainer)
    assert created_app.state.container.agent_service is not None
    assert created_app.state.container.tool_registry is not None
    assert created_app.state.container.retrieval_service is not None
    assert created_app.state.container.guardrail_policy is not None
    assert created_app.state.container.account_domain_service is not None
    assert created_app.state.container.account_investigation_service is not None
    assert created_app.state.container.audit_service is not None
    assert created_app.state.container.ops_workflow_service is not None
    assert created_app.state.container.mcp_sdk_adapter is not None
    assert created_app.state.container.knowledge_service is not None
    assert created_app.state.container.risk_service is not None
    assert created_app.state.container.trade_service is not None
    assert created_app.state.container.operations_service is not None
    assert created_app.state.container.storage_bundle is not None
    assert created_app.state.container.chat_persistence_coordinator is not None
    assert created_app.state.container.redis_chat_context_store is not None


def test_chat_route_uses_app_level_container_dependencies() -> None:
    class FakeAgentService:
        def __init__(self) -> None:
            self.received_commands: list[ChatCommand] = []

        def handle_command(
            self,
            command: ChatCommand,
            registry: ToolRegistry | None = None,
        ) -> AgentResponse:
            self.received_commands.append(command)
            return AgentResponse(
                reply_text="fake-agent-response",
                tool_names=["knowledge.search"],
            )

    class FakeRegistry:
        def get_tool(self, tool_name: str) -> MCPToolDefinition | None:
            return MCPToolDefinition(
                name=tool_name,
                domain="knowledge",
                description="Fake tool description.",
            )

        def list_tool_names(self) -> list[str]:
            return ["knowledge.search"]

        def invoke(
            self,
            tool_name: str,
            request_payload: dict[str, object] | None = None,
        ) -> ToolInvocationResult:
            return ToolInvocationResult(
                tool_name=tool_name,
                domain="knowledge",
                invocation_status="completed",
                request_payload=request_payload or {},
                response_payload={"source": "fake-container"},
            )

    original_container = app.state.container
    fake_agent_service = FakeAgentService()
    fake_registry = FakeRegistry()
    app.state.container = ApplicationContainer(
        agent_service=fake_agent_service,
        tool_registry=fake_registry,
        retrieval_service=original_container.retrieval_service,
        guardrail_policy=original_container.guardrail_policy,
        account_domain_service=original_container.account_domain_service,
        account_investigation_service=original_container.account_investigation_service,
        audit_service=original_container.audit_service,
        ops_workflow_service=original_container.ops_workflow_service,
        mcp_sdk_adapter=original_container.mcp_sdk_adapter,
            knowledge_service=original_container.knowledge_service,
            knowledge_ingestion_service=original_container.knowledge_ingestion_service,
            risk_service=original_container.risk_service,
            risk_batch_score_service=original_container.risk_batch_score_service,
            trade_service=original_container.trade_service,
        operations_service=original_container.operations_service,
        storage_bundle=original_container.storage_bundle,
        chat_persistence_coordinator=original_container.chat_persistence_coordinator,
        redis_chat_context_store=original_container.redis_chat_context_store,
        auth_service=original_container.auth_service,
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/chat",
            json={
                "user_role": "analyst",
                "message_text": "Search the policy playbook.",
            },
        )
    finally:
        app.state.container = original_container

    assert response.status_code == 200
    assert response.json()["reply_text"] == "fake-agent-response"
    assert fake_agent_service.received_commands == [
        ChatCommand(
            user_role="analyst",
                message_text="Search the policy playbook.",
                session_id=None,
                recent_messages=[],
                user_id=1,
                authorization_context={
                    "user_id": 1,
                    "username": "analyst_demo",
                    "roles": ("analyst",),
                    "access_level": "internal",
                    "allowed_access_levels": ("internal",),
                },
            )
    ]


def test_tool_route_uses_app_level_registry_dependency() -> None:
    class FakeRegistry:
        def __init__(self) -> None:
            self.invocations: list[tuple[str, dict[str, object] | None]] = []

        def invoke(
            self,
            tool_name: str,
            request_payload: dict[str, object] | None = None,
        ) -> ToolInvocationResult:
            self.invocations.append((tool_name, request_payload))
            return ToolInvocationResult(
                tool_name=tool_name,
                domain="trade",
                invocation_status="completed",
                request_payload=request_payload or {},
                response_payload={"source": "fake-container"},
            )

    original_container = app.state.container
    fake_registry = FakeRegistry()
    app.state.container = ApplicationContainer(
        agent_service=original_container.agent_service,
        tool_registry=fake_registry,
        retrieval_service=original_container.retrieval_service,
        guardrail_policy=original_container.guardrail_policy,
        account_domain_service=original_container.account_domain_service,
        account_investigation_service=original_container.account_investigation_service,
        audit_service=original_container.audit_service,
        ops_workflow_service=original_container.ops_workflow_service,
        mcp_sdk_adapter=original_container.mcp_sdk_adapter,
            knowledge_service=original_container.knowledge_service,
            knowledge_ingestion_service=original_container.knowledge_ingestion_service,
            risk_service=original_container.risk_service,
            risk_batch_score_service=original_container.risk_batch_score_service,
            trade_service=original_container.trade_service,
        operations_service=original_container.operations_service,
        storage_bundle=original_container.storage_bundle,
        chat_persistence_coordinator=original_container.chat_persistence_coordinator,
        redis_chat_context_store=original_container.redis_chat_context_store,
        auth_service=original_container.auth_service,
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/tools/trade-query-metrics",
            json={"query": "trade wallet volume gamma"},
        )
    finally:
        app.state.container = original_container

    assert response.status_code == 200
    assert response.json()["response_payload"]["source"] == "fake-container"
    assert fake_registry.invocations == [
        (
                "trade.query_metrics",
                {
                    "query": "trade wallet volume gamma",
                    "authorization_context": {
                        "user_id": 1,
                        "username": "analyst_demo",
                        "roles": ("analyst",),
                        "access_level": "internal",
                        "allowed_access_levels": ("internal",),
                    },
                },
        )
    ]


def test_account_investigation_route_uses_app_level_service_dependency() -> None:
    class FakeAccountInvestigationService:
        def __init__(self) -> None:
            self.received_account_ids: list[str] = []

        def get_account_investigation(
            self,
            account_id: str,
        ) -> dict[str, object] | None:
            self.received_account_ids.append(account_id)
            return {
                "account_overview": {"account_id": account_id, "source": "fake-container"},
                "recent_activity": {"account_id": account_id},
                "risk_profile": {"account_id": account_id},
                "trade_metrics": {"account_id": account_id},
            }

    original_container = app.state.container
    fake_account_investigation_service = FakeAccountInvestigationService()
    app.state.container = ApplicationContainer(
        agent_service=original_container.agent_service,
        tool_registry=original_container.tool_registry,
        retrieval_service=original_container.retrieval_service,
        guardrail_policy=original_container.guardrail_policy,
        account_domain_service=original_container.account_domain_service,
        account_investigation_service=fake_account_investigation_service,
        audit_service=original_container.audit_service,
        ops_workflow_service=original_container.ops_workflow_service,
        mcp_sdk_adapter=original_container.mcp_sdk_adapter,
            knowledge_service=original_container.knowledge_service,
            knowledge_ingestion_service=original_container.knowledge_ingestion_service,
            risk_service=original_container.risk_service,
            risk_batch_score_service=original_container.risk_batch_score_service,
            trade_service=original_container.trade_service,
        operations_service=original_container.operations_service,
        storage_bundle=original_container.storage_bundle,
        chat_persistence_coordinator=original_container.chat_persistence_coordinator,
        redis_chat_context_store=original_container.redis_chat_context_store,
        auth_service=original_container.auth_service,
    )

    try:
        client = TestClient(app)
        response = client.get("/accounts/acct-atlas-01/investigation")
    finally:
        app.state.container = original_container

    assert response.status_code == 200
    assert response.json()["account_overview"]["source"] == "fake-container"
    assert fake_account_investigation_service.received_account_ids == ["acct-atlas-01"]
