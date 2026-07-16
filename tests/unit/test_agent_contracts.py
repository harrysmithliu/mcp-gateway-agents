import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend.agent.service as agent_service_module
from backend.agent.models import AgentResponse, ChatCommand, ChatHistoryMessage
from backend.agent.service import AgentService
from backend.api.app import app
from backend.mcp_gateway.registry import MCPToolDefinition, ToolInvocationResult, build_default_registry
from backend.storage.chat_persistence import ChatPersistenceExchange


def test_handle_command_returns_structured_chat_result() -> None:
    agent_service = AgentService(
        planner_override_output="knowledge.search, risk.score_account"
    )
    registry = build_default_registry()

    result = agent_service.handle_command(
        ChatCommand(
            user_role="analyst",
            message_text="Search policy guidance and score this borrower account.",
            session_id="session-r1-001",
            recent_messages=[
                ChatHistoryMessage(role="user", content="Previous question"),
            ],
        ),
        registry=registry,
    )

    assert isinstance(result.reply_text, str)
    assert result.session_id == "session-r1-001"
    assert result.tool_names == ["knowledge.search", "risk.score_account"]
    assert [item.tool_name for item in result.planned_tool_calls] == result.tool_names
    assert [item.tool_name for item in result.tool_invocation_results] == result.tool_names
    assert result.planner_result is not None
    assert result.planner_result.used_fallback is False


def test_agent_does_not_expose_citations_from_unavailable_knowledge_result() -> None:
    result = AgentService._extract_retrieval_citations(
        [
            ToolInvocationResult(
                tool_name="knowledge.search",
                domain="knowledge",
                invocation_status="unavailable",
                response_payload={
                    "result_status": "unavailable",
                    "citations": [
                        {
                            "document_id": "doc-1",
                            "title": "Unavailable source",
                        }
                    ],
                },
            )
        ]
    )

    assert result == []


def test_rule_planner_does_not_route_risk_review_to_ops() -> None:
    tool_names, _, _, _ = AgentService().plan_tool_calls(
        normalized_role="analyst",
        normalized_text="Review the risk score for the Gamma account.",
        registry=build_default_registry(),
    )

    assert tool_names == ["risk.score_account"]


def test_handle_command_uses_passed_registry(monkeypatch) -> None:
    class FakeRegistry:
        def __init__(self) -> None:
            self.invocations: list[tuple[str, dict[str, object] | None]] = []

        def get_tool(self, tool_name: str) -> MCPToolDefinition | None:
            if tool_name != "knowledge.search":
                return None
            return MCPToolDefinition(
                name="knowledge.search",
                domain="knowledge",
                description="Fake knowledge tool.",
            )

        def list_tool_names(self) -> list[str]:
            return ["knowledge.search"]

        def preview_knowledge_matches(
            self,
            query_text: str,
            limit: int = 3,
        ) -> list[dict[str, object]]:
            return [
                {
                    "document_id": "fake-doc",
                    "title": "Fake Knowledge",
                    "summary": "Fake summary",
                    "matched_terms": ["policy"],
                    "match_score": 1,
                }
            ][:limit]

        def invoke(
            self,
            tool_name: str,
            request_payload: dict[str, object] | None = None,
        ) -> ToolInvocationResult:
            self.invocations.append((tool_name, request_payload))
            return ToolInvocationResult(
                tool_name=tool_name,
                domain="knowledge",
                invocation_status="completed",
                request_payload=request_payload or {},
                response_payload={"source": "fake-registry"},
            )

    monkeypatch.setattr(
        agent_service_module,
        "build_default_registry",
        lambda: (_ for _ in ()).throw(AssertionError("default registry should not be built")),
    )

    fake_registry = FakeRegistry()
    result = AgentService(
        planner_override_output="knowledge.search"
    ).handle_command(
        ChatCommand(
            user_role="analyst",
            message_text="Search the policy playbook.",
        ),
        registry=fake_registry,
    )

    assert result.tool_names == ["knowledge.search"]
    assert result.session_id is None
    assert fake_registry.invocations == [
        (
            "knowledge.search",
            {
                "user_role": "analyst",
                "message_text": "Search the policy playbook.",
            },
        )
    ]


def test_handle_chat_facade_builds_chat_command(monkeypatch) -> None:
    captured_command: dict[str, ChatCommand] = {}

    def capture_handle_command(
        self: AgentService,
        command: ChatCommand,
        registry=None,
    ) -> AgentResponse:
        captured_command["command"] = command
        return AgentResponse(reply_text="captured")

    monkeypatch.setattr(AgentService, "handle_command", capture_handle_command)

    result = AgentService().handle_chat(
        user_role="Analyst",
        message_text="Review this account.",
        session_id="session-r1-002",
        recent_messages=[
            ChatHistoryMessage(role="user", content="Earlier question"),
            ChatHistoryMessage(role="assistant", content="Earlier answer"),
        ],
    )

    assert result.reply_text == "captured"
    assert captured_command["command"] == ChatCommand(
        user_role="Analyst",
        message_text="Review this account.",
        session_id="session-r1-002",
        recent_messages=[
            ChatHistoryMessage(role="user", content="Earlier question"),
            ChatHistoryMessage(role="assistant", content="Earlier answer"),
        ],
    )


def test_chat_route_preserves_structured_contract_after_command_refactor() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": "Please search policy guidance and review this borrower account.",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert set(payload) == {
        "session_id",
        "reply_text",
        "tool_names",
        "planned_tool_calls",
        "tool_invocation_results",
        "evidence",
        "actions",
        "citations",
        "planner_result",
        "cache_status",
        "cache_reason",
    }


def test_handle_command_routes_through_chat_persistence_coordinator() -> None:
    class FakeCoordinator:
        def __init__(self) -> None:
            self.started: list[ChatPersistenceExchange] = []
            self.finished: list[tuple[ChatPersistenceExchange, AgentResponse]] = []

        def start_exchange(
            self,
            command: ChatCommand,
            normalized_role: str,
            normalized_text: str,
        ) -> ChatPersistenceExchange:
            exchange = ChatPersistenceExchange(
                user_role=command.user_role,
                normalized_role=normalized_role,
                message_text=command.message_text,
                normalized_text=normalized_text,
                requested_session_id=command.session_id,
                effective_session_id=command.session_id,
                recent_messages=list(command.recent_messages),
            )
            self.started.append(exchange)
            return exchange

        def finish_exchange(
            self,
            exchange: ChatPersistenceExchange,
            agent_response: AgentResponse,
        ) -> object:
            self.finished.append((exchange, agent_response))
            return object()

    coordinator = FakeCoordinator()
    agent_service = AgentService(
        planner_override_output="knowledge.search",
        chat_persistence_coordinator=coordinator,
    )
    registry = build_default_registry()

    result = agent_service.handle_command(
        ChatCommand(
            user_role="Analyst",
            message_text="Search the policy playbook.",
            session_id="session-round-1",
            recent_messages=[
                ChatHistoryMessage(role="user", content="Earlier question"),
            ],
        ),
        registry=registry,
    )

    assert len(coordinator.started) == 1
    assert coordinator.started[0].normalized_role == "analyst"
    assert coordinator.started[0].normalized_text == "Search the policy playbook."
    assert coordinator.started[0].requested_session_id == "session-round-1"
    assert len(coordinator.finished) == 1
    assert coordinator.finished[0][0] is coordinator.started[0]
    assert coordinator.finished[0][1] is result
    assert result.session_id == "session-round-1"


def test_handle_command_loads_recent_messages_from_redis_context_store() -> None:
    class FakeRedisChatContextStore:
        def __init__(self) -> None:
            self.load_calls: list[tuple[str | None, int | None]] = []

        def load_recent_messages(
            self,
            session_id: str | None,
            limit: int | None = None,
        ) -> list[ChatHistoryMessage]:
            self.load_calls.append((session_id, limit))
            return [
                ChatHistoryMessage(role="user", content="Redis previous question"),
                ChatHistoryMessage(role="assistant", content="Redis previous answer"),
            ]

    captured_recent_messages: dict[str, list[ChatHistoryMessage]] = {}

    def capture_plan_tool_calls_with_langchain(
        self: AgentService,
        normalized_role: str,
        normalized_text: str,
        registry,
        session_id: str | None = None,
        recent_messages: list[ChatHistoryMessage] | None = None,
    ):
        _ = self, normalized_role, normalized_text, registry, session_id
        captured_recent_messages["recent_messages"] = list(recent_messages or [])
        return (
            ["knowledge.search"],
            [],
            [],
            [],
            type(
                "PlannerResultStub",
                (),
                {
                    "planner_source": "rule_fallback",
                    "raw_output_text": None,
                    "candidate_tool_names": [],
                    "selected_tool_names": ["knowledge.search"],
                    "used_fallback": True,
                    "fallback_reason": "captured",
                },
            )(),
        )

    redis_store = FakeRedisChatContextStore()
    agent_service = AgentService(
        redis_chat_context_store=redis_store,
    )
    registry = build_default_registry()

    original_method = AgentService.plan_tool_calls_with_langchain
    AgentService.plan_tool_calls_with_langchain = capture_plan_tool_calls_with_langchain
    try:
        agent_service.handle_command(
            ChatCommand(
                user_role="analyst",
                message_text="Search the policy playbook.",
                session_id="session-round-7-redis",
                recent_messages=[],
            ),
            registry=registry,
        )
    finally:
        AgentService.plan_tool_calls_with_langchain = original_method

    assert redis_store.load_calls == [("session-round-7-redis", 6)]
    assert captured_recent_messages["recent_messages"] == [
        ChatHistoryMessage(role="user", content="Redis previous question"),
        ChatHistoryMessage(role="assistant", content="Redis previous answer"),
    ]
