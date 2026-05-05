from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 从.env文件读取配置，编码设置为utf-8，且大小写不敏感
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # alias 表示对应的环境变量名
    # 应用基础配置
    app_name: str = Field(default="local-llm-fastapi-api", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_docs: bool = Field(default=True, alias="ENABLE_DOCS")

    # 安全与跨域
    api_keys: str = Field(default="dev-key-1", alias="API_KEYS")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # 模型与后端
    default_model: str = Field(default="qwen/qwen3.5-9b", alias="DEFAULT_MODEL")
    model_catalog: str = Field(default="qwen/qwen3.5-9b", alias="MODEL_CATALOG")
    llm_backend: str = Field(default="lmstudio_openai", alias="LLM_BACKEND")
    lmstudio_base_url: str = Field(
        default="http://127.0.0.1:1234/v1", alias="LMSTUDIO_BASE_URL"
    )
    lmstudio_api_key: str = Field(default="", alias="LMSTUDIO_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", alias="OPENAI_BASE_URL"
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    request_timeout_seconds: int = Field(default=60, alias="REQUEST_TIMEOUT_SECONDS")
    model_timeout_seconds: int = Field(default=45, alias="MODEL_TIMEOUT_SECONDS")
    max_concurrent_requests: int = Field(default=4, alias="MAX_CONCURRENT_REQUESTS")
    rate_limit_rpm: int = Field(default=60, alias="RATE_LIMIT_RPM")

    # 监控
    prometheus_enabled: bool = Field(default=True, alias="PROMETHEUS_ENABLED")

    # 三个派生属性，把逗号字符串转为列表
    @property
    def api_key_list(self) -> List[str]:
        return [x.strip() for x in self.api_keys.split(",") if x.strip()]

    @property
    def cors_origin_list(self) -> List[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def model_list(self) -> List[str]:
        return [x.strip() for x in self.model_catalog.split(",") if x.strip()]


# 单例式获取
@lru_cache
def get_settings() -> Settings:
    """
    第一次调用时创建 Settings()；

    后续调用直接复用缓存对象，不重复读取解析环境变量。

    好处：性能更稳、全局配置一致。
    """
    return Settings()


"""
@lru_cache
def get_settings() -> Settings:
    ...
等价于：

get_settings = lru_cache()(get_settings)
也就是先调用一次 lru_cache()（使用默认参数），再把返回的装饰器应用到函数上。

补充一下默认值（functools.lru_cache）：

maxsize=128
typed=False
所以你的 get_settings() 实际上是“最多缓存 128 组不同参数调用结果，且不区分类型缓存键”。
但这个函数本身没有参数，因此实际上只会缓存 1 个结果（第一次创建的 Settings() 对象）。
"""
