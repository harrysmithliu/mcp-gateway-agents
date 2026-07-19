import json
import logging
import re

from fastapi.testclient import TestClient

from backend.api.app import app
from backend.observability.context import (
    REQUEST_ID_HEADER,
    reset_request_id,
    set_request_id,
)
from backend.observability.logging import StructuredJsonFormatter


def test_request_middleware_generates_and_returns_request_id() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        response.headers[REQUEST_ID_HEADER],
    )


def test_request_middleware_preserves_safe_inbound_request_id() -> None:
    request_id = "78bb5a9e-9bc9-4867-aee2-e01922ab6bd9"
    response = TestClient(app).get(
        "/health",
        headers={REQUEST_ID_HEADER: request_id},
    )

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == request_id


def test_request_middleware_replaces_non_uuid_inbound_request_id() -> None:
    response = TestClient(app).get(
        "/health",
        headers={REQUEST_ID_HEADER: "trace-20260718-request"},
    )

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] != "trace-20260718-request"
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        response.headers[REQUEST_ID_HEADER],
    )


def test_structured_formatter_includes_request_id_and_excludes_unknown_extras() -> None:
    context_token = set_request_id("78bb5a9e-9bc9-4867-aee2-e01922ab6bd9")
    try:
        record = logging.LogRecord(
            name="backend.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="safe event",
            args=(),
            exc_info=None,
        )
        record.tool_name = "knowledge.search"
        record.secret = "must-not-appear"

        payload = json.loads(StructuredJsonFormatter().format(record))
    finally:
        reset_request_id(context_token)

    assert payload["request_id"] == "78bb5a9e-9bc9-4867-aee2-e01922ab6bd9"
    assert payload["tool_name"] == "knowledge.search"
    assert "secret" not in payload
