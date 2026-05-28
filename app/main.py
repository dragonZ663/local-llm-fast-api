import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth_routes import router as auth_router
from app.api.routes import router
from app.auth.database import init_database
from app.config import get_settings
from app.infra.logging import RequestContextMiddleware, setup_logging
from app.infra.metrics import (http_requests_total, render_metrics,
                               request_latency_seconds)
from app.infra.request_context import get_request_id
from app.middleware.auth import JWTAuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.schemas import APIErrorResponse

settings = get_settings()
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    if settings.app_env != "dev" and settings.jwt_secret == "dev-change-me":
        raise RuntimeError("Set a strong JWT_SECRET before running outside dev")
    yield


app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    lifespan=lifespan,
)


"""中间件链（请求进来后按顺序经过）"""

# 一般用于请求上下文（比如 request_id）
app.add_middleware(RequestContextMiddleware)

# 按用户限流（需在鉴权之后执行，见下方注册顺序）
app.add_middleware(RateLimitMiddleware)

# JWT 鉴权（登录/注册路径放行）
app.add_middleware(JWTAuthMiddleware)

# 跨域控制，来源列表来自配置 cors_origin_list，并暴露 x-request-id 给前端。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list if settings.cors_origin_list else ["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)

# 路由注册
app.include_router(auth_router)
app.include_router(router)


""" 监控中间件（自定义 @app.middleware("http")) """


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - started

    # 请求耗时：request_latency_seconds（按 path 打标签）
    request_latency_seconds.labels(path=request.url.path).observe(duration)

    # 请求总数：http_requests_total（按 method/path/status_code）
    http_requests_total.labels(
        method=request.method,
        path=request.url.path,
        status_code=str(response.status_code),
    ).inc()
    return response


""" 统一异常处理 """


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    """HTTPException 处理:

    处理 FastAPI/业务抛出的 HTTPException;
    返回统一结构 APIErrorResponse;
    request_id 优先从上下文取，拿不到就回退到请求头。
    """
    body = APIErrorResponse(
        code=f"http_{exc.status_code}",
        message=str(exc.detail),
        request_id=get_request_id() or request.headers.get("x-request-id", "unknown"),
        details={"path": request.url.path},
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """兜底 Exception 处理:

    捕获未处理异常，统一返回 500;
    对外隐藏具体错误信息（仅固定文案），但在 details 中保留异常类型名。
    """
    body = APIErrorResponse(
        code="internal_error",
        message="Internal server error",
        request_id=get_request_id() or request.headers.get("x-request-id", "unknown"),
        details={"path": request.url.path, "error": type(exc).__name__},
    )
    return JSONResponse(status_code=500, content=body.model_dump())


@app.get("/metrics")
async def metrics():
    """暴露 Prometheus 风格监控数据（由 render_metrics() 生成）。
    用于被 Prometheus 抓取。"""
    return render_metrics()


""" 整体请求流（简化版）
请求进入 -> 经过中间件(CORS、限流、鉴权、上下文)(注册顺序与请求进入顺序相反)。
命中业务路由(router)。
成功则被 metrics_middleware 记录耗时和计数后返回。
失败则进入异常处理器，返回统一错误结构。 

【中间件对于请求的执行顺序】
对 app.add_middleware(...)：

请求进入（inbound）：后加的先执行（LIFO）
响应返回（outbound）：先加的后返回（FIFO）
也就是一个“洋葱模型”：

外层 middleware 先收到请求
调 call_next 进入内层
最后到路由
返回时再一层层退出
你的注册顺序是：

RequestContextMiddleware
RateLimitMiddleware
JWTAuthMiddleware
CORSMiddleware
所以请求进入顺序会是（理论上）：

CORSMiddleware -> JWTAuth -> RateLimit -> RequestContext -> 路由
官方文档：https://fastapi.tiangolo.com/zh/tutorial/middleware/?h=%E4%B8%AD%E9%97%B4%E4%BB%B6#multiple-middleware-execution-order
"""
