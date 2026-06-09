"""Dependencias FastAPI do Sistema Master Web."""
from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .config import get_settings
from .services.auth_service import resolve_admin

MASTER_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = MASTER_DIR / "templates"
STATIC_DIR = MASTER_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_runtime(request: Request):
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Runtime indisponivel.")
    return runtime


def template_context(request: Request, admin=None, **extra):
    settings = get_settings()
    ctx = {
        "request": request,
        "admin": admin,
        "app_title": settings.app_title,
        "app_build": settings.app_build,
        "service_name": "master-web",
    }
    ctx.update(extra)
    return ctx


def resolve_admin_or_redirect(request: Request):
    admin = resolve_admin(request)
    if not admin:
        return None, RedirectResponse("/login", status_code=303)
    return admin, None
