"""CSS do painel web — carregado inline (nao depende de /static em producao)."""
from __future__ import annotations

from pathlib import Path

MASTER_CSS_FILE = Path(__file__).resolve().parent / "static" / "master" / "css" / "master.css"
_css_cache: str | None = None
_css_mtime: float | None = None


def load_master_css() -> str:
    global _css_cache, _css_mtime
    try:
        mtime = MASTER_CSS_FILE.stat().st_mtime
    except OSError:
        return "/* master.css ausente */"
    if _css_cache is None or _css_mtime != mtime:
        from app.cdn.urls import patch_css_static_urls

        _css_cache = patch_css_static_urls(MASTER_CSS_FILE.read_text(encoding="utf-8"))
        _css_mtime = mtime
    return _css_cache
