import json
import logging
import time
from typing import Any, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.infra.request_context import (get_request_id, new_request_id,
                                       set_request_id)


def setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s: %(message)s",
    )

    # 1. 创建一个文件处理器，日志写入 app.log
    app_handler = logging.FileHandler("logs/app.log")

    # 2. 设置日志格式
    app_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s"))

    # 3. 获取名为 "app" 的 logger 实例
    app_logger = logging.getLogger("app")

    # 4. 禁止向父 logger（root）传播日志，避免重复输出
    app_logger.propagate = True

    # 5. 将文件处理器添加到 "app" logger
    app_logger.addHandler(app_handler)


def log_event(event: str, **kwargs: Any) -> None:
    payload: Dict[str, Any] = {"event": event, "request_id": get_request_id(), **kwargs}
    # "app" 是 logger 的名称（name） ，用于标识和获取一个特定的日志记录器实例。
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
