from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BFAI API"
    app_version: str = "0.1.0"
    environment: str = "production"
    debug: bool = False
    docs_enabled: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    site_url: AnyHttpUrl | None = None

    database_url: str = ""
    redis_url: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: AnyHttpUrl = "https://openrouter.ai/api/v1"
    openrouter_app_title: str = "BFAI API"

    cors_origins: list[str] = Field(default_factory=list)
    cors_allow_credentials: bool = False
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_csv(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
