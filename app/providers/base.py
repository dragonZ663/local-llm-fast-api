from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List

from app.schemas import ChatMessage


class UpstreamLLMError(Exception):
    def __init__(self, message: str, status_code: int = 502, details: Dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def stream_chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        raise NotImplementedError
