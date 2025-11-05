"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    use_llm: bool = False

    database_url: str = "postgresql+asyncpg://workflow:workflow@localhost:5432/workflow_automation"
    database_echo: bool = False
    pool_size: int = 5
    max_overflow: int = 5
    pool_recycle: int = 1800

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    compression_max_chars: int = 800
    compression_target_ratio: float = 0.6
    qc_pass_threshold: float = 0.7
    max_rework_cycles: int = 2

    memory_top_k: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
