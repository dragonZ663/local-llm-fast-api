import asyncio
import json
import time
import uuid
from typing import AsyncIterator

from fastapi import HTTPException

from app.config import get_settings
from app.infra.request_context import get_request_id
from app.providers.base import UpstreamLLMError
from app.schemas import (
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkChoiceDelta,
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from app.services.model_router import ModelRouter


class ChatService:
    def __init__(self) -> None:
        self.router = ModelRouter()
        self.sem = asyncio.Semaphore(get_settings().max_concurrent_requests)

    async def create_completion(self, payload: ChatCompletionRequest) -> ChatCompletionResponse:
        provider = self.router.get_provider(payload.model)
        try:
            async with self.sem:
                data = await asyncio.wait_for(
                    provider.chat_completion(payload.model, payload.messages, payload.temperature, payload.max_tokens),
                    timeout=get_settings().model_timeout_seconds,
                )
        except UpstreamLLMError as exc:
            raise HTTPException(status_code=exc.status_code, detail={"message": str(exc), "details": exc.details}) from exc
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        usage = {
            "prompt_tokens": data.get("prompt_tokens", sum(len(m.content.split()) for m in payload.messages)),
            "completion_tokens": data.get("completion_tokens", len(data["content"].split())),
            "total_tokens": 0,
        }
        usage["total_tokens"] = data.get("total_tokens", usage["prompt_tokens"] + usage["completion_tokens"])
        return ChatCompletionResponse(
            id=completion_id,
            created=int(time.time()),
            model=payload.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": data["content"]},
                    finish_reason="stop",
                )
            ],
            usage=usage,
            request_id=get_request_id(),
        )

    async def stream_completion_sse(self, payload: ChatCompletionRequest) -> AsyncIterator[str]:
        provider = self.router.get_provider(payload.model)
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        try:
            # 用全局信号量 Semaphore(max_concurrent_requests) 控制并发
            async with self.sem:
                # 每拿到一个 token，会包装成 ChatCompletionChunk（OpenAI 风格）并输出
                async for token in provider.stream_chat_completion(
                    payload.model, payload.messages, payload.temperature, payload.max_tokens
                ):
                    chunk = ChatCompletionChunk(
                        id=completion_id,
                        created=int(time.time()),
                        model=payload.model,
                        choices=[
                            ChatCompletionChunkChoice(
                                index=0,
                                delta=ChatCompletionChunkChoiceDelta(role="assistant", content=token),
                                finish_reason=None,
                            )
                        ],
                        request_id=get_request_id(),
                    )
                    yield f"data: {json.dumps(chunk.model_dump(), ensure_ascii=True)}\n\n"
                # 上游结束后，服务层会主动再发两条
                final_chunk = ChatCompletionChunk(
                    id=completion_id,
                    created=int(time.time()),
                    model=payload.model,
                    choices=[
                        ChatCompletionChunkChoice(
                            index=0,
                            delta=ChatCompletionChunkChoiceDelta(),
                            finish_reason="stop",
                        )
                    ],
                    request_id=get_request_id(),
                )
                yield f"data: {json.dumps(final_chunk.model_dump(), ensure_ascii=True)}\n\n"
                yield "data: [DONE]\n\n"
        except UpstreamLLMError as exc:
            # 捕获后不会抛 HTTPException，而是往流里发
            error_event = {
                "error": {
                    "code": "upstream_error",
                    "message": str(exc),
                    "details": exc.details,
                    "request_id": get_request_id(),
                }
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=True)}\n\n"
            yield "data: [DONE]\n\n"
