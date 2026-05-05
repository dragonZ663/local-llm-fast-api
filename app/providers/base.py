from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List

from app.schemas import ChatMessage


class UpstreamLLMError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 502,
        details: Dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


# 继承 ABC 成为抽象类，强制实现 chat_completion 和 stream_chat_completion 方法
# 并标记为异步方法
class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, str]:
        """
        生成模型响应的异步方法。

        :param model: 要使用的模型名称
        :param messages: 对话消息列表
        :param temperature: 温度参数，控制生成的随机性
        :param max_tokens: 最大令牌数，限制生成的响应长度
        :return: 包含模型响应的字典
        """
        raise NotImplementedError

    @abstractmethod
    def stream_chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """
        流式生成模型响应的异步方法。

        :param model: 要使用的模型名称
        :param messages: 对话消息列表
        :param temperature: 温度参数，控制生成的随机性
        :param max_tokens: 最大令牌数，限制生成的响应长度
        :return: 一个异步迭代器，每次迭代返回模型响应的一部分
        """
        raise NotImplementedError
