"""Credenciais Supabase — env vars ou data/supabase_credentials.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_CREDENTIALS_FILE = _ROOT / "data" / "supabase_credentials.json"


def _load_file_credentials():
    if not _CREDENTIALS_FILE.is_file():
        return {}
    try:
        with open(_CREDENTIALS_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def get_url():
    return (
        os.environ.get("SUPABASE_URL", "").strip()
        or _load_file_credentials().get("SUPABASE_URL", "").strip()
    )


def get_api_key():
    return (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.environ.get("SUPABASE_ANON_KEY", "").strip()
        or _load_file_credentials().get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or _load_file_credentials().get("SUPABASE_ANON_KEY", "").strip()
    )


def is_configured():
    return bool(get_url() and get_api_key())
