from app.config import get_settings
from app.providers.base import BaseLLMProvider
from app.providers.lmstudio_openai import LMStudioOpenAIProvider
from app.providers.mock_local import MockLocalProvider
from app.providers.deepseek_openai import DeepSeekOpenAIProvider
from app.enums import LLMBackend


class ModelRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.local_provider = MockLocalProvider()
        self.lmstudio_provider = LMStudioOpenAIProvider()
        self.deepseek_provider = (
            DeepSeekOpenAIProvider() if self.settings.llm_backend == LLMBackend.DEEPSEEK_OPENAI else None
        )

    def get_provider(self, model: str) -> BaseLLMProvider:
        if self.settings.llm_backend == LLMBackend.DEEPSEEK_OPENAI:
            if self.deepseek_provider is None:
                raise ValueError("DeepSeek OpenAI provider is not initialized")
            return self.deepseek_provider
        if self.settings.llm_backend == LLMBackend.LMSTUDIO_OPENAI:
            return self.lmstudio_provider
        return self.local_provider
