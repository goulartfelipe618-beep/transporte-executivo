"""Rotas web — autenticacao administrativa."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.master.repositories.session_repository import audit_login_event

from ...dependencies import template_context, templates
from ...services.auth_service import create_web_session, login_admin, logout_admin, resolve_admin
from ...services.captcha_service import new_captcha_code, store_login_captcha, verify_login_captcha

router = APIRouter(tags=["master-auth"])


def _login_context(request: Request, *, error="", email=""):
    captcha = new_captcha_code()
    store_login_captcha(request, captcha)
    return template_context(request, error=error, email=email, captcha_code=captcha)


@router.get("/")
async def root(request: Request):
    if resolve_admin(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/login.html",
        _login_context(request),
    )


@router.get("/login")
async def login_page(request: Request):
    if resolve_admin(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/login.html",
        _login_context(request),
    )


@router.get("/login/captcha")
async def login_captcha_refresh(request: Request):
    if resolve_admin(request):
        return JSONResponse({"code": ""})
    captcha = new_captcha_code()
    store_login_captcha(request, captcha)
    return JSONResponse({"code": captcha})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    captcha: str = Form(""),
):
    if not verify_login_captcha(request, captcha):
        audit_login_event(
            email=str(email or "").strip(),
            success=False,
            detail="captcha invalido",
            metadata={"ip": _client_ip(request)},
        )
        return templates.TemplateResponse(
            request,
            "master/login.html",
            _login_context(request, error="Codigo de seguranca invalido.", email=email),
            status_code=401,
        )
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
            _login_context(request, error=error or "E-mail ou senha invalidos.", email=email),
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
