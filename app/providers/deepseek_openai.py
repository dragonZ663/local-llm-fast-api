from typing import AsyncIterator, Dict, List, cast

from openai import APIConnectionError, APIError, APIStatusError, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.config import get_settings
from app.providers.base import BaseLLMProvider, UpstreamLLMError
from app.schemas import ChatMessage


class DeepSeekOpenAIProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_BACKEND=deepseek_openai")
        self.client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            timeout=self.settings.model_timeout_seconds,
        )

    async def chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, str]:
        try:
            completion = await self.client.chat.completions.create(
                model=model,
                messages=cast(
                    List[ChatCompletionMessageParam], [m.model_dump() for m in messages]
                ),
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}}
            )
        except APIStatusError as exc:
            upstream_status = exc.status_code
            raise UpstreamLLMError(
                message=f"DeepSeek OpenAI upstream HTTP error: {upstream_status}",
                status_code=upstream_status if 400 <= upstream_status < 600 else 502,
                details={
                    "upstream_status": str(upstream_status),
                    "endpoint": "/chat/completions",
                },
            ) from exc
        except (APIConnectionError, APIError) as exc:
            raise UpstreamLLMError(
                message="DeepSeek OpenAI upstream request failed",
                status_code=502,
                details={"endpoint": "/chat/completions", "error": type(exc).__name__},
            ) from exc

        content = completion.choices[0].message.content or ""
        usage = completion.usage
        return {
            "content": content,
            "prompt_tokens": str(usage.prompt_tokens if usage else "0"),
            "completion_tokens": str(usage.completion_tokens if usage else "0"),
            "total_tokens": str(usage.total_tokens if usage else "0"),
        }

    async def stream_chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        try:
            print("DeepSeek OpenAIProvider: Starting stream_chat_completion")
            stream = await self.client.chat.completions.create(
                model=model,
                messages=cast(
                    List[ChatCompletionMessageParam], [m.model_dump() for m in messages]
                ),
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                extra_body={"thinking": {"type": "disabled"}}
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                token = chunk.choices[0].delta.content
                if token:
                    yield token
        except APIStatusError as exc:
            upstream_status = exc.status_code
            raise UpstreamLLMError(
                message=f"DeepSeek OpenAI upstream HTTP error: {upstream_status}",
                status_code=upstream_status if 400 <= upstream_status < 600 else 502,
                details={
                    "upstream_status": str(upstream_status),
                    "endpoint": "/chat/completions",
                },
            ) from exc
        except (APIConnectionError, APIError) as exc:
            raise UpstreamLLMError(
                message="DeepSeek OpenAI upstream request failed",
                status_code=502,
                details={"endpoint": "/chat/completions", "error": type(exc).__name__},
            ) from exc
