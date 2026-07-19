import json
import logging
from datetime import datetime, timezone

from backend.observability.context import get_request_id


SAFE_LOG_FIELDS = (
    "http_method",
    "http_path",
    "http_status",
    "latency_ms",
    "tool_name",
    "transport_mode",
    "retrieval_source",
    "top_k",
    "error_type",
)


class StructuredJsonFormatter(logging.Formatter):
    """Emit a minimal correlation-friendly JSON event without payload data."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = get_request_id()
        if request_id is not None:
            payload["request_id"] = request_id
        for field_name in SAFE_LOG_FIELDS:
            field_value = getattr(record, field_name, None)
            if field_value is not None:
                payload[field_name] = field_value
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, default=str, sort_keys=True)


def configure_structured_logging(level_name: str = "INFO") -> None:
    """Configure the project logger once without modifying third-party loggers."""

    logger = logging.getLogger("backend")
    if any(getattr(handler, "_project_structured", False) for handler in logger.handlers):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    handler._project_structured = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))
    logger.propagate = True
