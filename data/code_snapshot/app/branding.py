"""Identidade visual global — nome e fonte a partir de Configuracoes."""
from __future__ import annotations

import tkinter.font as tkfont

from .settings_store import load_settings

DEFAULT_BRAND = "Nexus Transfer"
_FALLBACK_FONT = "Segoe UI"


_FONT_FAMILIES_CACHE = None


def _font_families():
    global _FONT_FAMILIES_CACHE
    if _FONT_FAMILIES_CACHE is not None:
        return _FONT_FAMILIES_CACHE
    try:
        import tkinter as tk

        if tk._get_default_root() is None:
            return {}
        _FONT_FAMILIES_CACHE = {item.lower(): item for item in tkfont.families()}
    except RuntimeError:
        return {}
    return _FONT_FAMILIES_CACHE or {}


def resolve_font_family(name):
    raw = str(name or "").strip()
    if not raw:
        return _FALLBACK_FONT
    families = _font_families()
    for candidate in (raw, raw.title(), raw.capitalize(), raw.upper()):
        match = families.get(candidate.lower()) if families else None
        if match:
            return match
    if not families:
        return raw.title()
    compact = raw.replace(" ", "")
    for family in families.values():
        if family.replace(" ", "").lower() == compact.lower():
            return family
    return _FALLBACK_FONT


def brand_display_name(settings=None):
    settings = settings or load_settings()
    name = str(settings.get("nome_projeto") or settings.get("empresa") or DEFAULT_BRAND).strip()
    return name or DEFAULT_BRAND


def brand_initials(name=None, settings=None):
    name = str(name or brand_display_name(settings)).strip()
    parts = [part for part in name.replace("-", " ").split() if part]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return (name[:2] or "NT").upper()


def load_branding(settings=None):
    settings = settings or load_settings()
    family = resolve_font_family(settings.get("fonte_global"))
    return {
        "nome_projeto": brand_display_name(settings),
        "fonte_global": family,
        "fonte_solicitada": str(settings.get("fonte_global") or "").strip(),
        "logo_global": str(settings.get("logo_global") or "").strip(),
    }


def build_font_tokens(family):
    family = resolve_font_family(family)
    return {
        "brand": (family, 15, "bold"),
        "heading": (family, 14, "bold"),
        "title": (family, 18, "bold"),
        "subtitle": (family, 10),
        "body": (family, 10),
        "small": (family, 9),
        "tiny": (family, 8),
        "mono": ("Consolas", 10),
        "mono_lg": ("Consolas", 20, "bold"),
        "semibold_md": (family, 10, "bold"),
        "semibold_sm": (family, 9, "bold"),
    }


def apply_branding(settings=None):
    from . import theme

    settings = settings or load_settings()
    theme.apply_theme(settings)
    branding = load_branding(settings)
    theme.FONTS.clear()
    theme.FONTS.update(build_font_tokens(branding["fonte_global"]))
    theme.ACTIVE_FONT_FAMILY = branding["fonte_global"]
    theme.ACTIVE_BRAND_NAME = branding["nome_projeto"]
    return branding
