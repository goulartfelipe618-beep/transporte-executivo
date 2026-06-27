"""Dependencias FastAPI do Sistema Master Web."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.branding import brand_display_name, brand_initials
from app.cdn.urls import cdn_base, static_url, web_media_url

from .config import get_settings
from .services.auth_service import is_totp_session_verified, resolve_admin
from .web_assets import load_master_css

MASTER_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = MASTER_DIR / "templates"
STATIC_DIR = MASTER_DIR / "static"
MASTER_STATIC_DIR = STATIC_DIR / "master"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["master_css"] = load_master_css
templates.env.globals["static_url"] = static_url
templates.env.globals["web_media_url"] = web_media_url
templates.env.globals["cdn_base"] = cdn_base

NAV_TITLES = {
    "dashboard": "Dashboard",
    "metricas": "Metricas",
    "agenda": "Agenda",
    "reservas": "Reservas",
    "receptivos": "Receptivos",
    "empresas": "Empresas",
    "clientes": "Clientes",
    "motoristas": "Motoristas",
    "veiculos": "Veiculos",
    "abrangencia": "Abrangencia Operacional",
    "solicitacoes": "Solicitacoes",
    "leads_empresas": "Leads de Empresas",
    "leads_motoristas": "Leads de Motoristas",
    "financeiro": "Financeiro",
    "configuracoes": "Configuracoes",
    "automacoes": "Automacoes",
    "geolocalizador": "Geolocalizador",
    "rede": "Rede Comercial",
}


def get_runtime(request: Request):
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Runtime indisponivel.")
    return runtime


def template_context(request: Request, admin=None, **extra):
    settings = get_settings()
    brand = brand_display_name()
    active_nav = extra.get("active_nav", "")
    nav_open = {
        "financeiro": active_nav == "financeiro" or bool(extra.get("active_finance_tab")),
        "transfer": active_nav in {"solicitacoes", "reservas", "receptivos", "geolocalizador"},
        "rede": active_nav == "rede" or bool(extra.get("rede_tab")),
        "sistema": active_nav in {"configuracoes", "automacoes", "leads_empresas", "leads_motoristas"},
    }
    ctx = {
        "request": request,
        "admin": admin,
        "app_title": settings.app_title,
        "app_build": settings.app_build,
        "service_name": "master-web",
        "brand_name": brand,
        "brand_initials": brand_initials(brand),
        "today": datetime.now().strftime("%d/%m/%Y"),
        "page_title": NAV_TITLES.get(active_nav, settings.app_title),
        "nav_open": nav_open,
    }
    ctx.update(extra)
    return ctx


def _is_totp_exempt_path(path: str) -> bool:
    if path.startswith("/static/") or path in {"/favicon.ico", "/health", "/api/health", "/api/deploy-info"}:
        return True
    if path.startswith("/rastreio"):
        return True
    if path.startswith("/api/v1/master/health"):
        return True
    if path in {"/", "/login", "/login/captcha", "/logout"}:
        return True
    from app.totp_auth import is_totp_enabled

    if not is_totp_enabled():
        return path.startswith("/configuracoes/2fa")
    if path == "/login/2fa":
        return True
    return False


def resolve_admin_or_redirect(request: Request):
    admin = resolve_admin(request)
    if not admin:
        return None, RedirectResponse("/login", status_code=303)

    path = request.url.path.rstrip("/") or "/"
    if _is_totp_exempt_path(path):
        return admin, None

    from app.totp_auth import is_totp_enabled

    if not is_totp_enabled():
        return admin, RedirectResponse("/configuracoes/2fa?obrigatorio=1", status_code=303)
    if not is_totp_session_verified(request):
        return admin, RedirectResponse("/login/2fa", status_code=303)
    return admin, None
