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
            # 自动管理客户端生命周期（自动关闭连接）
            async with httpx.AsyncClient(
                base_url=self.settings.lmstudio_base_url,
                timeout=timeout,
                trust_env=False,  # 不读取环境变量中的代理配置（避免使用系统代理）
            ) as client:
                resp = await client.post(
                    "/chat/completions", json=payload, headers=self._headers()
                )
                # - 检查响应状态码
                # - 如果状态码 >= 400（如 404、500），抛出 HTTPStatusError 异常
                resp.raise_for_status()
                # - 将响应体解析为 JSON 格式
                # - 返回 Python 字典对象
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            upstream_status = exc.response.status_code
            raise UpstreamLLMError(
                message=f"LM Studio upstream HTTP error: {upstream_status}",
                status_code=upstream_status if 400 <= upstream_status < 600 else 502,
                details={
                    "upstream_status": str(upstream_status),
                    "endpoint": "/chat/completions",
                },
            ) from exc  # 将原始异常 exc 作为新异常的原因
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
                async with client.stream(
                    "POST", "/chat/completions", json=payload, headers=self._headers()
                ) as resp:
                    resp.raise_for_status()
                    # 逐行读取
                    async for line in resp.aiter_lines():
                        # 只处理 data: ... 行
                        if not line or not line.startswith("data: "):
                            continue
                        data_payload = line[6:].strip()
                        # data: [DONE] -> 结束
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
                details={
                    "upstream_status": str(upstream_status),
                    "endpoint": "/chat/completions",
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamLLMError(
                message="LM Studio upstream request failed",
                status_code=502,
                details={"endpoint": "/chat/completions", "error": type(exc).__name__},
            ) from exc
