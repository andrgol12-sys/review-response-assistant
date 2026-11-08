from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    target_site_url: str = "http://127.0.0.1:8000"
    worker_api_token: str = "change-me"
    worker_poll_interval: int = 10
    state_file_path: str = "data/state.json"
    ai_author_name: str = "AI Support"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    telegram_bot_token: str = ""
    telegram_user_chat_id: str = ""
    telegram_chat_id: str = Field(default="", deprecated=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
