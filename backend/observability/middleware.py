import logging
from time import perf_counter

from fastapi import Request, Response

from backend.observability.context import (
    REQUEST_ID_HEADER,
    build_request_id,
    reset_request_id,
    set_request_id,
)


logger = logging.getLogger(__name__)


async def add_request_observability(
    request: Request,
    call_next,
) -> Response:
    """Attach one correlation ID to the request context and response boundary."""

    request_id = build_request_id(request.headers.get(REQUEST_ID_HEADER))
    context_token = set_request_id(request_id)
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "HTTP request failed",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "latency_ms": round((perf_counter() - started_at) * 1000),
            },
        )
        raise
    else:
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "latency_ms": round((perf_counter() - started_at) * 1000),
            },
        )
        return response
    finally:
        reset_request_id(context_token)
