from functools import lru_cache

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BFAI API"
    app_version: str = "0.1.0"
    environment: str = "production"
    app_env: str | None = None
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
    openrouter_fast_model: str = "deepseek/deepseek-v4-flash:free"
    openrouter_smart_model: str = "z-ai/glm-4.5-air:free"
    openrouter_fallback_model: str = "openai/gpt-oss-120b:free"
    openrouter_timeout_seconds: float = 60
    openrouter_max_retries: int = 2

    youtube_summary_cache_ttl_seconds: int = 86400
    youtube_transcript_timeout_seconds: float = 20
    youtube_summary_max_tokens: int = 900
    youtube_summary_temperature: float = 0.2
    youtube_summary_max_transcript_chars: int = 30000
    ai_prompt_cost_per_million_tokens: float = 0
    ai_completion_cost_per_million_tokens: float = 0

    api_key_auth_enabled: bool = True

    cors_origins: str = ""
    cors_allow_credentials: bool = False
    allowed_hosts: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def _parse_csv(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return self._parse_csv(self.cors_origins)

    @property
    def allowed_host_list(self) -> list[str]:
        hosts = self._parse_csv(self.allowed_hosts)
        if not hosts or "*" in hosts:
            return ["*"]

        healthcheck_hosts = ["localhost", "127.0.0.1", "::1"]
        return list(dict.fromkeys([*hosts, *healthcheck_hosts]))

    @property
    def is_production(self) -> bool:
        return (self.app_env or self.environment).lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
