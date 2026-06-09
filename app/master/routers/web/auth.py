"""Rotas web — autenticacao administrativa."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.master.repositories.session_repository import audit_login_event

from ...dependencies import template_context, templates
from ...services.auth_service import create_web_session, login_admin, logout_admin, resolve_admin

router = APIRouter(tags=["master-auth"])


@router.get("/")
async def root(request: Request):
    if resolve_admin(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/login.html",
        template_context(request, error="", email=""),
    )


@router.get("/login")
async def login_page(request: Request):
    if resolve_admin(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/login.html",
        template_context(request, error="", email=""),
    )


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
):
    admin, error = login_admin(email, password)
    if not admin:
        audit_login_event(
            email=str(email or "").strip(),
            success=False,
            detail=error or "credenciais invalidas",
            metadata={"ip": _client_ip(request)},
        )
        return templates.TemplateResponse(
            request,
            "master/login.html",
            template_context(request, error=error or "E-mail ou senha invalidos.", email=email),
            status_code=401,
        )
    create_web_session(request, admin)
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    logout_admin(request)
    return RedirectResponse("/login", status_code=303)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or ""
    return ""
