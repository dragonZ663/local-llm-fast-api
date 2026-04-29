from app.providers.base import BaseLLMProvider
from app.providers.lmstudio_openai import LMStudioOpenAIProvider
from app.providers.mock_local import MockLocalProvider
from app.providers.openai_sdk import OpenAISDKProvider
from app.config import get_settings


class ModelRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.local_provider = MockLocalProvider()
        self.lmstudio_provider = LMStudioOpenAIProvider()
        self.openai_provider = OpenAISDKProvider() if self.settings.llm_backend == "openai_sdk" else None

    def get_provider(self, model: str) -> BaseLLMProvider:
        if self.settings.llm_backend == "openai_sdk":
            if self.openai_provider is None:
                raise ValueError("OpenAI SDK provider is not initialized")
            return self.openai_provider
        if self.settings.llm_backend == "lmstudio_openai":
            return self.lmstudio_provider
        return self.local_provider
