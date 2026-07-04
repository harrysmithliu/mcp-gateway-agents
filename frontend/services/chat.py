import json
from dataclasses import dataclass, field
from urllib import error, request


@dataclass(slots=True)
class ChatApiResponse:
    reply_text: str
    tool_names: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


def post_chat_message(
    user_role: str,
    message_text: str,
    api_base_url: str = "http://localhost:8000",
    timeout_seconds: float = 5.0,
) -> ChatApiResponse:
    payload = json.dumps(
        {
            "user_role": user_role,
            "message_text": message_text,
        }
    ).encode("utf-8")

    chat_request = request.Request(
        url=f"{api_base_url.rstrip('/')}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(chat_request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError("Unable to reach the chat API.") from exc

    return ChatApiResponse(
        reply_text=response_payload["reply_text"],
        tool_names=response_payload.get("tool_names", []),
        evidence=response_payload.get("evidence", []),
        actions=response_payload.get("actions", []),
    )
