import json
import logging
import time
from typing import Any, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.infra.request_context import get_request_id, new_request_id, set_request_id


def setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(message)s")


def log_event(event: str, **kwargs: Any) -> None:
    payload: Dict[str, Any] = {"event": event, "request_id": get_request_id(), **kwargs}
    logging.getLogger("app").info(json.dumps(payload, ensure_ascii=True))


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", new_request_id())
        set_request_id(request_id)
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["x-request-id"] = request_id
        log_event(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        return response
