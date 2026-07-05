import json
from dataclasses import dataclass, field
from urllib import error, request


@dataclass(slots=True)
class ChatApiPlannedToolCall:
    tool_name: str
    domain: str
    description: str


@dataclass(slots=True)
class ChatApiToolInvocationResult:
    tool_name: str
    domain: str
    invocation_status: str
    request_payload: dict[str, object] = field(default_factory=dict)
    response_payload: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ChatApiResponse:
    reply_text: str
    tool_names: list[str] = field(default_factory=list)
    planned_tool_calls: list[ChatApiPlannedToolCall] = field(default_factory=list)
    tool_invocation_results: list[ChatApiToolInvocationResult] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


def _post_json(
    endpoint_path: str,
    payload: dict[str, object],
    api_base_url: str = "http://localhost:8000",
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    chat_request = request.Request(
        url=f"{api_base_url.rstrip('/')}/{endpoint_path.lstrip('/')}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(chat_request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError("Unable to reach the chat API.") from exc


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
    api_base_url: str = "http://localhost:8000",
    timeout_seconds: float = 5.0,
) -> ChatApiResponse:
    response_payload = _post_json(
        endpoint_path="/chat",
        payload={
            "user_role": user_role,
            "message_text": message_text,
        },
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    )

    return ChatApiResponse(
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
    )


def post_knowledge_search(
    query: str,
    api_base_url: str = "http://localhost:8000",
    timeout_seconds: float = 5.0,
) -> ChatApiToolInvocationResult:
    response_payload = _post_json(
        endpoint_path="/tools/knowledge-search",
        payload={"query": query},
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    )
    return _parse_tool_invocation_result(response_payload)


def post_risk_score_account(
    query: str,
    api_base_url: str = "http://localhost:8000",
    timeout_seconds: float = 5.0,
) -> ChatApiToolInvocationResult:
    response_payload = _post_json(
        endpoint_path="/tools/risk-score-account",
        payload={"query": query},
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    )
    return _parse_tool_invocation_result(response_payload)


def post_trade_query_metrics(
    query: str,
    api_base_url: str = "http://localhost:8000",
    timeout_seconds: float = 5.0,
) -> ChatApiToolInvocationResult:
    response_payload = _post_json(
        endpoint_path="/tools/trade-query-metrics",
        payload={"query": query},
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    )
    return _parse_tool_invocation_result(response_payload)


def post_ops_create_alert_or_action(
    query: str,
    api_base_url: str = "http://localhost:8000",
    timeout_seconds: float = 5.0,
) -> ChatApiToolInvocationResult:
    response_payload = _post_json(
        endpoint_path="/tools/ops-create-alert-or-action",
        payload={"query": query},
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    )
    return _parse_tool_invocation_result(response_payload)
