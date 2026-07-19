from contextvars import ContextVar, Token
import re
from uuid import UUID, uuid4


REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def build_request_id(inbound_value: str | None = None) -> str:
    """Use a bounded safe inbound ID or create a server-owned UUID."""

    if inbound_value is not None:
        candidate = inbound_value.strip()
        if _REQUEST_ID_PATTERN.fullmatch(candidate):
            return str(UUID(candidate))
    return str(uuid4())


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(request_id: str) -> Token[str | None]:
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)
