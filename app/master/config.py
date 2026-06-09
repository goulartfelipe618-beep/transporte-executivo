"""Configuracao do Sistema Master Web."""
from __future__ import annotations

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_secret() -> str:
    for key in ("MASTER_SECRET_KEY", "GATEWAY_WEBHOOK_SECRET", "SECRET_KEY"):
        value = os.environ.get(key, "").strip()
        if len(value) >= 32:
            return value
    return "nexus-master-dev-secret-change-in-production-32chars"


class MasterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MASTER_", extra="ignore")

    secret_key: str = Field(default_factory=_default_secret)
    session_cookie: str = "master_session"
    session_max_age: int = 60 * 60 * 24 * 7
    port: int = 8772
    app_title: str = "Central Operacional Master"
    app_build: str = ""

    @property
    def https_only(self) -> bool:
        return os.environ.get("APP_ENV", "").strip().lower() == "production"


def get_settings() -> MasterSettings:
    from app.version import APP_BUILD

    settings = MasterSettings()
    settings.app_build = APP_BUILD
    return settings
