from app.providers.base import BaseLLMProvider
from app.providers.lmstudio_openai import LMStudioOpenAIProvider
from app.providers.mock_local import MockLocalProvider
from app.config import get_settings


class ModelRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.local_provider = MockLocalProvider()
        self.lmstudio_provider = LMStudioOpenAIProvider()

    def get_provider(self, model: str) -> BaseLLMProvider:
        if self.settings.llm_backend == "lmstudio_openai":
            return self.lmstudio_provider
        return self.local_provider
