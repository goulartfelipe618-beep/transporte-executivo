"""Resolução de URLs públicas via CDN Cloudflare R2."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import httpx

from .config import get_r2_config
from .storage import generate_presigned_url, public_url_for_key


def cdn_enabled() -> bool:
    return get_r2_config()["configured"]


def cdn_base() -> str:
    cfg = get_r2_config()
    if not cfg["configured"]:
        return ""
    if cfg["prefix"]:
        return f"{cfg['public_base']}/{cfg['prefix']}"
    return cfg["public_base"]


def _local_static_url(path: str) -> str:
    path = path.strip().lstrip("/")
    if path.startswith("motor/"):
        return f"/static/{path[6:]}"
    if path.startswith("master/"):
        return f"/static/master/{path[7:]}"
    return f"/static/{path}"


def _static_file_on_disk(path: str) -> Path | None:
    """Retorna arquivo estatico local quando existir no disco."""
    rel = str(path or "").strip().lstrip("/")
    if rel.startswith("static/"):
        rel = rel[7:]
    app_dir = Path(__file__).resolve().parents[1]
    if rel.startswith("master/"):
        candidate = app_dir / "master" / "static" / "master" / rel[7:]
    elif rel.startswith("motor/"):
        candidate = app_dir / "static" / rel[6:]
    else:
        candidate = app_dir / "master" / "static" / "master" / rel
    return candidate if candidate.is_file() else None


def static_r2_key(path: str) -> str:
    path = path.strip().lstrip("/")
    if path.startswith("static/"):
        path = path[7:]
    if not path.startswith(("motor/", "master/")):
        path = f"motor/{path}"
    return f"{get_r2_config()['prefix']}/static/{path}".strip("/")


def static_url(path: str) -> str:
    path = str(path or "").strip()
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        return path
    local = _local_static_url(path)
    if _static_file_on_disk(path) is not None:
        return local
    cfg = get_r2_config()
    if not cfg["configured"]:
        return local
    return public_url_for_key(static_r2_key(path))


def web_media_url(value: str, *, branding_slug: str = "logo") -> str:
    """URL HTTP servivel pelo navegador para midia de configuracao."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return raw
    cfg = get_r2_config()
    if raw.startswith("r2private:"):
        return f"/media/branding/{branding_slug}"
    if raw.startswith("r2key:"):
        if not cfg["configured"]:
            return ""
        return public_url_for_key(raw[len("r2key:"):].lstrip("/"))
    if cfg["configured"] and cfg["public_base"] in raw:
        return raw
    if os.path.isfile(raw):
        return f"/media/branding/{branding_slug}"
    return ""


def resolve_media_url(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    cfg = get_r2_config()
    if raw.startswith("r2private:"):
        key = raw[len("r2private:"):].lstrip("/")
        signed = generate_presigned_url(key)
        return signed or raw
    if raw.startswith(("http://", "https://")):
        return raw
    if cfg["configured"] and cfg["public_base"] in raw:
        return raw
    if os.path.isfile(raw):
        return raw
    if raw.startswith("r2key:"):
        return public_url_for_key(raw[len("r2key:"):].lstrip("/"))
    return raw


def fetch_media_bytes(value: str, *, timeout: float = 20.0) -> bytes | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.startswith("r2private:"):
        url = resolve_media_url(raw)
        if not url:
            return None
        try:
            response = httpx.get(url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError:
            return None
    if raw.startswith(("http://", "https://")):
        try:
            response = httpx.get(raw, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError:
            return None
    path = Path(raw)
    if path.is_file():
        return path.read_bytes()
    return None


def materialize_media_file(value: str, *, suffix: str = ".bin") -> str:
    data = fetch_media_bytes(value)
    if not data:
        return ""
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.write(data)
    handle.close()
    return handle.name


def patch_css_static_urls(css: str) -> str:
    if not css:
        return css
    cfg = get_r2_config()
    if not cfg["configured"]:
        return css

    def _replace(match: re.Match) -> str:
        quote = match.group(1)
        path = match.group(2)
        if path.startswith(("http://", "https://", "data:")):
            return match.group(0)
        cleaned = path.lstrip("/")
        if cleaned.startswith("static/master/"):
            cleaned = cleaned[len("static/master/"):]
            url = static_url(f"master/{cleaned}")
        elif cleaned.startswith("static/"):
            cleaned = cleaned[len("static/"):]
            url = static_url(f"motor/{cleaned}")
        elif cleaned.startswith("master/"):
            url = static_url(cleaned)
        else:
            url = static_url(cleaned)
        return f"url({quote}{url}{quote})"

    return re.sub(r'url\((["\']?)([^"\')]+)\1\)', _replace, css)
