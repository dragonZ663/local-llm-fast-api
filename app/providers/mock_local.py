import asyncio
from typing import AsyncIterator, Dict, List

from app.providers.base import BaseLLMProvider
from app.schemas import ChatMessage


class MockLocalProvider(BaseLLMProvider):
    async def chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, str]:
        user_messages = [m.content for m in messages if m.role == "user"]
        prompt = user_messages[-1] if user_messages else "empty prompt"
        content = f"[{model}] Echo: {prompt[:max_tokens]}"
        return {"content": content}

    async def stream_chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        result = await self.chat_completion(model, messages, temperature, max_tokens)
        words = result["content"].split(" ")
        for word in words:
            await asyncio.sleep(0.02)
            yield f"{word} "
