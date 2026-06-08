"""URLs publicas dos portais — dominios EasyPanel / producao."""
from __future__ import annotations

import os

DEFAULT_API_BASE = "https://api.transporteexecutivo.com"
DEFAULT_SISTEMA_BASE = "https://sistema.transporteexecutivo.com"
DEFAULT_DRIVER_BASE = "https://driver.transporteexecutivo.com"
DEFAULT_BUSINESS_BASE = "https://business.transporteexecutivo.com"
DEFAULT_ENGINE_BASE = "https://engine.transporteexecutivo.com"


def _env(name, default):
    return os.environ.get(name, "").strip() or default


def api_base_url():
    return _env("INTEGRACAO_API_BASE_URL", _env("GATEWAY_API_BASE_URL", DEFAULT_API_BASE)).rstrip("/")


def sistema_web_base():
    return _env("SISTEMA_WEB_BASE_URL", DEFAULT_SISTEMA_BASE).rstrip("/")


def driver_portal_base():
    return _env("DRIVER_PORTAL_BASE_URL", DEFAULT_DRIVER_BASE).rstrip("/")


def company_portal_base():
    return _env("COMPANY_PORTAL_BASE_URL", DEFAULT_BUSINESS_BASE).rstrip("/")


def engine_base():
    return _env("ENGINE_BASE_URL", DEFAULT_ENGINE_BASE).rstrip("/")


def company_portal_link(company):
    company_id = str((company or {}).get("id", "")).strip()
    codigo = str((company or {}).get("portal_codigo", "")).strip().upper()
    if company_id and codigo:
        return f"{company_portal_base()}/{company_id}/{codigo}"
    legacy = str((company or {}).get("portal_key", "")).strip()
    if legacy:
        return f"{company_portal_base()}/empresa/{legacy}"
    return ""


def driver_portal_link(driver, slug=None):
    from .portal_server import driver_key

    key = slug or driver_key(driver or {})
    return f"{driver_portal_base()}/driver/{key}"


def network_booking_link(partner):
    slug = str((partner or {}).get("slug", "")).strip()
    code = str((partner or {}).get("codigo", partner.get("codigo_acesso", ""))).strip().upper()
    if slug and code:
        return f"{engine_base()}/{slug}/{code}"
    return ""
