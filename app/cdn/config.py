"""Configuração Cloudflare R2 (S3-compatible)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _load_dotenv() -> None:
    env_file = Path(".env")
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_r2_config() -> dict:
    _load_dotenv()
    enabled = _truthy(os.environ.get("R2_ENABLED", "true"))
    account_id = os.environ.get("R2_ACCOUNT_ID", "").strip()
    access_key = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
    bucket = os.environ.get("R2_BUCKET_NAME", "transporte-executivo-system").strip()
    endpoint = os.environ.get("R2_ENDPOINT_URL", "").strip()
    if not endpoint and account_id:
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    public_base = os.environ.get(
        "R2_PUBLIC_BASE_URL",
        "https://cdn-system.transporteexecutivo.com",
    ).strip().rstrip("/")
    prefix = os.environ.get("R2_PREFIX", "system").strip().strip("/")
    signed_expires = int(os.environ.get("R2_SIGNED_URL_EXPIRES", "3600") or "3600")
    auto_upload = _truthy(os.environ.get("R2_AUTO_UPLOAD", "true"))
    configured = bool(enabled and access_key and secret_key and bucket and endpoint)
    return {
        "enabled": enabled,
        "configured": configured,
        "account_id": account_id,
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket": bucket,
        "endpoint": endpoint,
        "public_base": public_base,
        "prefix": prefix,
        "signed_expires": max(60, signed_expires),
        "auto_upload": auto_upload,
    }


def clear_r2_config_cache() -> None:
    get_r2_config.cache_clear()
