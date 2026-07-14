from dataclasses import dataclass, field

from frontend.services.api import DEFAULT_API_BASE_URL, build_api_client
from frontend.services.retrieval import (
    RetrievalCitation,
    parse_retrieval_citations,
)


@dataclass(slots=True)
class ChatApiPlannedToolCall:
    tool_name: str
    domain: str
    description: str


@dataclass(slots=True)
class ChatApiHistoryMessage:
    role: str
    content: str


@dataclass(slots=True)
class ChatApiToolInvocationResult:
    tool_name: str
    domain: str
    invocation_status: str
    request_payload: dict[str, object] = field(default_factory=dict)
    response_payload: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ChatApiPlannerResult:
    planner_source: str
    raw_output_text: str | None = None
    candidate_tool_names: list[str] = field(default_factory=list)
    selected_tool_names: list[str] = field(default_factory=list)
    used_fallback: bool = False
    fallback_reason: str | None = None
    retrieval_status: str | None = None
    retrieval_source: str | None = None
    retrieval_result_count: int = 0
    grounded_chunk_count: int = 0
    grounding_truncated: bool = False


@dataclass(slots=True)
class ChatApiResponse:
    reply_text: str
    session_id: str | None = None
    tool_names: list[str] = field(default_factory=list)
    planned_tool_calls: list[ChatApiPlannedToolCall] = field(default_factory=list)
    tool_invocation_results: list[ChatApiToolInvocationResult] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    citations: list[RetrievalCitation] = field(default_factory=list)
    planner_result: ChatApiPlannerResult | None = None


def _post_json(
    endpoint_path: str,
    payload: dict[str, object],
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(
        access_token=access_token,
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    ).post(endpoint_path, payload)


def _parse_tool_invocation_result(
    response_payload: dict[str, object],
) -> ChatApiToolInvocationResult:
    return ChatApiToolInvocationResult(
        tool_name=str(response_payload["tool_name"]),
        domain=str(response_payload["domain"]),
        invocation_status=str(response_payload["invocation_status"]),
        request_payload=dict(response_payload.get("request_payload", {})),
        response_payload=dict(response_payload.get("response_payload", {})),
    )


def post_chat_message(
    user_role: str,
    message_text: str,
    session_id: str | None = None,
    recent_messages: list[ChatApiHistoryMessage] | None = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> ChatApiResponse:
    request_kwargs = {
        "endpoint_path": "/chat",
        "payload": {
            "user_role": user_role,
            "message_text": message_text,
            "session_id": session_id,
            "recent_messages": [
                {
                    "role": recent_message.role,
                    "content": recent_message.content,
                }
                for recent_message in recent_messages or []
            ],
        },
        "api_base_url": api_base_url,
        "timeout_seconds": timeout_seconds,
    }
    if access_token is not None:
        request_kwargs["access_token"] = access_token
    response_payload = _post_json(**request_kwargs)

    return ChatApiResponse(
        session_id=response_payload.get("session_id"),
        reply_text=response_payload["reply_text"],
        tool_names=response_payload.get("tool_names", []),
        planned_tool_calls=[
            ChatApiPlannedToolCall(
                tool_name=planned_tool_call["tool_name"],
                domain=planned_tool_call["domain"],
                description=planned_tool_call["description"],
            )
            for planned_tool_call in response_payload.get("planned_tool_calls", [])
        ],
        tool_invocation_results=[
            ChatApiToolInvocationResult(
                tool_name=tool_invocation_result["tool_name"],
                domain=tool_invocation_result["domain"],
                invocation_status=tool_invocation_result["invocation_status"],
                request_payload=tool_invocation_result.get("request_payload", {}),
                response_payload=tool_invocation_result.get("response_payload", {}),
            )
            for tool_invocation_result in response_payload.get("tool_invocation_results", [])
        ],
        evidence=response_payload.get("evidence", []),
        actions=response_payload.get("actions", []),
        citations=parse_retrieval_citations(response_payload.get("citations")),
        planner_result=(
            ChatApiPlannerResult(
                planner_source=str(response_payload["planner_result"]["planner_source"]),
                raw_output_text=response_payload["planner_result"].get("raw_output_text"),
                candidate_tool_names=list(
                    response_payload["planner_result"].get("candidate_tool_names", [])
                ),
                selected_tool_names=list(
                    response_payload["planner_result"].get("selected_tool_names", [])
                ),
                used_fallback=bool(
                    response_payload["planner_result"].get("used_fallback", False)
                ),
                fallback_reason=response_payload["planner_result"].get("fallback_reason"),
                retrieval_status=response_payload["planner_result"].get("retrieval_status"),
                retrieval_source=response_payload["planner_result"].get("retrieval_source"),
                retrieval_result_count=int(
                    response_payload["planner_result"].get("retrieval_result_count", 0)
                    or 0
                ),
                grounded_chunk_count=int(
                    response_payload["planner_result"].get("grounded_chunk_count", 0)
                    or 0
                ),
                grounding_truncated=bool(
                    response_payload["planner_result"].get("grounding_truncated", False)
                ),
            )
            if response_payload.get("planner_result") is not None
            else None
        ),
    )


def post_knowledge_search(
    query: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> ChatApiToolInvocationResult:
    response_payload = _post_json(
        endpoint_path="/tools/knowledge-search",
        payload={"query": query},
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
        access_token=access_token,
    )
    return _parse_tool_invocation_result(response_payload)


def post_risk_score_account(
    query: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> ChatApiToolInvocationResult:
    response_payload = _post_json(
        endpoint_path="/tools/risk-score-account",
        payload={"query": query},
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
        access_token=access_token,
    )
    return _parse_tool_invocation_result(response_payload)


def post_trade_query_metrics(
    query: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> ChatApiToolInvocationResult:
    response_payload = _post_json(
        endpoint_path="/tools/trade-query-metrics",
        payload={"query": query},
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
        access_token=access_token,
    )
    return _parse_tool_invocation_result(response_payload)


def post_ops_create_alert_or_action(
    query: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> ChatApiToolInvocationResult:
    response_payload = _post_json(
        endpoint_path="/tools/ops-create-alert-or-action",
        payload={"query": query},
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
        access_token=access_token,
    )
    return _parse_tool_invocation_result(response_payload)
