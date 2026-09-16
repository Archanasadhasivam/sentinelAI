"""
Central config. Reads from environment / .env. Nothing here should crash the
app if GROQ_API_KEY is missing — modules that need it must check
`settings.groq_enabled` and degrade gracefully (see §7.5 of the build spec).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str | None = None
    groq_fast_model: str = "openai/gpt-oss-20b"
    groq_reasoning_model: str = "openai/gpt-oss-120b"
    groq_safety_model: str = "meta-llama/llama-guard-4-12b"

    database_url: str = "sqlite+aiosqlite:///./sentinelai.db"
    cors_origin: str = "http://localhost:3000"

    @property
    def groq_enabled(self) -> bool:
        return bool(self.groq_api_key) and self.groq_api_key != "gsk_your_key_here"


@lru_cache
def get_settings() -> Settings:
    return Settings()
