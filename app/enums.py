from enum import StrEnum

class LLMBackend(StrEnum):
    LMSTUDIO_OPENAI = "lmstudio_openai"
    DEEPSEEK_OPENAI = "deepseek_openai"
    MOCK_LOCAL = "mock_local"