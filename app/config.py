"""Application configuration."""

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = ".env" if Path(".env").is_file() else None


def _read_env_database_url() -> str:
    for key in ("DATABASE_URL", "database_url"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
        populate_by_name=True,
    )

    app_name: str = "Motor de Reservas Nexus Transfer"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    base_url: str = "https://api.transporteexecutivo.com"
    allowed_hosts: str = "api.transporteexecutivo.com"
    healthcheck_host: str = "api.transporteexecutivo.com"

    database_url: str = Field(
        default="",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    redis_url: str = ""
    redis_enabled: bool = False

    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    csrf_secret_key: str = Field(..., min_length=32)

    master_api_base_url: str = "https://api.transporteexecutivo.com"
    master_api_key: str = ""
    master_api_timeout: int = 30

    gateway_api_base_url: str = "https://api.transporteexecutivo.com"
    gateway_api_key: str = ""
    gateway_api_timeout: int = 30
    gateway_mock_fallback: bool = False

    supabase_url: str = ""
    supabase_anon_key: str = ""

    mercadopago_access_token: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    pix_provider_key: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@transporteexecutivo.com"

    rate_limit_per_minute: int = 60
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    cors_origins: str = "https://api.transporteexecutivo.com"

    @field_validator("allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def strip_value(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    overrides = {}
    database_url = _read_env_database_url()
    if database_url:
        overrides["database_url"] = database_url
    return Settings(**overrides)
