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
