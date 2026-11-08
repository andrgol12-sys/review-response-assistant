from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    local_database_url: str = ""
    postgres_db: str = "reviews_db"
    postgres_user: str = "reviews_user"
    postgres_password: str = "reviews_password"
    postgres_host: str = "db"
    postgres_port: int = 5432
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    worker_api_token: str = "change-me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        if self.local_database_url:
            return self.local_database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()
