import json
from typing import AsyncIterator, Dict, List

import httpx

from app.config import get_settings
from app.providers.base import BaseLLMProvider, UpstreamLLMError
from app.schemas import ChatMessage


class LMStudioOpenAIProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.lmstudio_api_key:
            headers["Authorization"] = f"Bearer {self.settings.lmstudio_api_key}"
        return headers

    async def chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, str]:
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        timeout = httpx.Timeout(self.settings.model_timeout_seconds)
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.lmstudio_base_url,
                timeout=timeout,
                trust_env=False,
            ) as client:
                resp = await client.post("/chat/completions", json=payload, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            upstream_status = exc.response.status_code
            raise UpstreamLLMError(
                message=f"LM Studio upstream HTTP error: {upstream_status}",
                status_code=upstream_status if 400 <= upstream_status < 600 else 502,
                details={"upstream_status": str(upstream_status), "endpoint": "/chat/completions"},
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamLLMError(
                message="LM Studio upstream request failed",
                status_code=502,
                details={"endpoint": "/chat/completions", "error": type(exc).__name__},
            ) from exc
        message = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return {
            "content": message,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

    async def stream_chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        timeout = httpx.Timeout(self.settings.model_timeout_seconds)
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.lmstudio_base_url,
                timeout=timeout,
                trust_env=False,
            ) as client:
                async with client.stream("POST", "/chat/completions", json=payload, headers=self._headers()) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_payload = line[6:].strip()
                        if data_payload == "[DONE]":
                            break
                        chunk = json.loads(data_payload)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        token = delta.get("content")
                        if token:
                            yield token
        except httpx.HTTPStatusError as exc:
            upstream_status = exc.response.status_code
            raise UpstreamLLMError(
                message=f"LM Studio upstream HTTP error: {upstream_status}",
                status_code=upstream_status if 400 <= upstream_status < 600 else 502,
                details={"upstream_status": str(upstream_status), "endpoint": "/chat/completions"},
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamLLMError(
                message="LM Studio upstream request failed",
                status_code=502,
                details={"endpoint": "/chat/completions", "error": type(exc).__name__},
            ) from exc
