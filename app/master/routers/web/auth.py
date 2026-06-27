"""Rotas web — autenticacao administrativa."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.master.repositories.session_repository import audit_login_event

from ...dependencies import template_context, templates
from ...services.auth_service import (
    create_web_session,
    is_totp_session_verified,
    login_admin,
    logout_admin,
    mark_totp_session_verified,
    post_login_redirect,
    resolve_admin,
)
from ...services.captcha_service import new_captcha_code, store_login_captcha, verify_login_captcha
from app.totp_auth import is_totp_enabled, verify_action_totp

router = APIRouter(tags=["master-auth"])


def _login_context(request: Request, *, error="", email=""):
    captcha = new_captcha_code()
    store_login_captcha(request, captcha)
    return template_context(request, error=error, email=email, captcha_code=captcha)


@router.get("/")
async def root(request: Request):
    admin = resolve_admin(request)
    if admin:
        return RedirectResponse(post_login_redirect(request), status_code=303)
    return templates.TemplateResponse(
        request,
        "master/login.html",
        _login_context(request),
    )


@router.get("/login")
async def login_page(request: Request):
    admin = resolve_admin(request)
    if admin:
        return RedirectResponse(post_login_redirect(request), status_code=303)
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
    return RedirectResponse(post_login_redirect(request), status_code=303)


@router.get("/login/2fa")
async def login_2fa_page(request: Request):
    admin = resolve_admin(request)
    if not admin:
        return RedirectResponse("/login", status_code=303)
    if not is_totp_enabled():
        return RedirectResponse("/configuracoes/2fa?obrigatorio=1", status_code=303)
    if is_totp_session_verified(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/login_2fa.html",
        template_context(request, error=""),
    )


@router.post("/login/2fa")
async def login_2fa_submit(request: Request, totp_code: str = Form("")):
    admin = resolve_admin(request)
    if not admin:
        return RedirectResponse("/login", status_code=303)
    if not is_totp_enabled():
        return RedirectResponse("/configuracoes/2fa?obrigatorio=1", status_code=303)
    ok, err = verify_action_totp(totp_code)
    if not ok:
        return templates.TemplateResponse(
            request,
            "master/login_2fa.html",
            template_context(request, error=err),
            status_code=401,
        )
    mark_totp_session_verified(request)
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
