"""Dependencias FastAPI do Sistema Master Web."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.branding import brand_display_name, brand_initials

from .config import get_settings
from .services.auth_service import resolve_admin
from .web_assets import load_master_css

MASTER_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = MASTER_DIR / "templates"
STATIC_DIR = MASTER_DIR / "static"
MASTER_STATIC_DIR = STATIC_DIR / "master"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["master_css"] = load_master_css

NAV_TITLES = {
    "dashboard": "Dashboard",
    "metricas": "Metricas",
    "agenda": "Agenda",
    "reservas": "Reservas",
    "empresas": "Empresas",
    "motoristas": "Motoristas",
    "veiculos": "Veiculos",
    "abrangencia": "Abrangencia Operacional",
    "solicitacoes": "Solicitacoes",
    "leads_empresas": "Leads de Empresas",
    "leads_motoristas": "Leads de Motoristas",
    "financeiro": "Financeiro",
    "configuracoes": "Configuracoes",
    "automacoes": "Automacoes",
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
    }
    ctx.update(extra)
    return ctx


def resolve_admin_or_redirect(request: Request):
    admin = resolve_admin(request)
    if not admin:
        return None, RedirectResponse("/login", status_code=303)
    return admin, None
