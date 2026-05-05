import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.schemas import (ChatCompletionRequest, HealthResponse, ModelCard,
                         ModelListResponse, ReadinessResponse)
from app.services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service=get_settings().app_name)


@router.get("/readyz", response_model=ReadinessResponse)
async def readyz() -> ReadinessResponse:
    settings = get_settings()
    upstream_status = "unknown"
    headers = {}
    if settings.lmstudio_api_key:
        headers["Authorization"] = f"Bearer {settings.lmstudio_api_key}"
    try:
        async with httpx.AsyncClient(
            base_url=settings.lmstudio_base_url, timeout=5, trust_env=False
        ) as client:
            resp = await client.get("/models", headers=headers)
            upstream_status = f"http_{resp.status_code}"
    except httpx.HTTPError:
        upstream_status = "unreachable"
    status = (
        "ready"
        if settings.model_list and upstream_status == "http_200"
        else "not_ready"
    )
    return ReadinessResponse(
        status=status,
        model_provider=settings.llm_backend,
        details={"models": settings.model_list, "upstream": upstream_status},
    )


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    return ModelListResponse(
        data=[
            ModelCard(id=m, metadata={"supports_stream": True, "supports_chat": True})
            for m in get_settings().model_list
        ]
    )


@router.post("/v1/chat/completions")
async def chat_completions(request: Request, payload: ChatCompletionRequest):
    if payload.model not in get_settings().model_list:
        raise HTTPException(status_code=404, detail=f"Unknown model: {payload.model}")
    if payload.stream:
        # StreamingResponse: FastAPI 提供的一个 流式响应类 ，用于实现 服务器端流式传输 。
        return StreamingResponse(
            chat_service.stream_completion_sse(payload), media_type="text/event-stream"
        )
    return await chat_service.create_completion(payload)
