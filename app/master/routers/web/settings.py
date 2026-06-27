"""Rotas web — Configuracoes do Sistema Master."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.totp_auth import (
    disable_totp,
    enable_totp,
    generate_totp_secret,
    is_totp_enabled,
    provisioning_uri,
    totp_qr_data_url,
    totp_status,
)

from ...dependencies import resolve_admin_or_redirect, template_context, templates
from ...services.auth_service import (
    clear_totp_session_verified,
    mark_totp_session_verified,
    post_login_redirect,
)
from ...services.settings_service import settings_page_context, update_settings

router = APIRouter(prefix="/configuracoes", tags=["master-settings"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


@router.get("")
async def settings_index(request: Request, editar: int = 0, saved: int = 0):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    warning = ""
    if saved:
        warning = str(request.session.pop("settings_warning", "") or "").strip()
    ctx = settings_page_context(
        editing=bool(editar),
        saved=bool(saved),
        warning=warning,
    )
    ctx.update({"admin": admin, "active_nav": "configuracoes"})
    return templates.TemplateResponse(
        request,
        "master/configuracoes/index.html",
        template_context(request, **ctx),
    )


@router.post("")
async def settings_save(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    form_data = _form_dict(await request.form())
    payload, errors, warning = update_settings(form_data)
    if errors:
        ctx = settings_page_context(editing=True, form=form_data, error=" ".join(errors))
        ctx.update({"admin": admin, "active_nav": "configuracoes"})
        return templates.TemplateResponse(
            request,
            "master/configuracoes/index.html",
            template_context(request, **ctx),
            status_code=400,
        )
    if warning:
        request.session["settings_warning"] = warning
    return RedirectResponse("/configuracoes?saved=1", status_code=303)


@router.get("/2fa")
async def totp_settings_page(request: Request, ok: str = "", obrigatorio: int = 0):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    setup_secret = str(request.session.get("totp_setup_secret", "") or "").strip()
    ctx = {
        "admin": admin,
        "active_nav": "configuracoes",
        "totp": totp_status(),
        "totp_enabled": is_totp_enabled(),
        "setup_secret": setup_secret if not is_totp_enabled() else "",
        "qr_data_url": totp_qr_data_url(provisioning_uri(setup_secret, totp_status()["account"])) if setup_secret else "",
        "error": "",
        "success_msg": ok.replace("+", " ") if ok else "",
        "obrigatorio": bool(obrigatorio) or not is_totp_enabled(),
    }
    return templates.TemplateResponse(
        request,
        "master/configuracoes/totp.html",
        template_context(request, **ctx),
    )


@router.post("/2fa/gerar")
async def totp_generate(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    if is_totp_enabled():
        return RedirectResponse("/configuracoes/2fa", status_code=303)
    request.session["totp_setup_secret"] = generate_totp_secret()
    return RedirectResponse("/configuracoes/2fa", status_code=303)


@router.post("/2fa/ativar")
async def totp_activate(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    form = await request.form()
    code = str(form.get("totp_code", "")).strip()
    secret = str(request.session.get("totp_setup_secret", "") or "").strip()
    account = totp_status()["account"]
    ok, err = enable_totp(secret, code, account_email=account)
    if not ok:
        ctx = {
            "admin": admin,
            "active_nav": "configuracoes",
            "totp": totp_status(),
            "totp_enabled": False,
            "setup_secret": secret,
            "qr_data_url": totp_qr_data_url(provisioning_uri(secret, account)) if secret else "",
            "error": err,
            "success_msg": "",
            "obrigatorio": not is_totp_enabled(),
        }
        return templates.TemplateResponse(
            request,
            "master/configuracoes/totp.html",
            template_context(request, **ctx),
            status_code=400,
        )
    request.session.pop("totp_setup_secret", None)
    mark_totp_session_verified(request)
    return RedirectResponse(post_login_redirect(request), status_code=303)


@router.post("/2fa/desativar")
async def totp_deactivate(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    form = await request.form()
    code = str(form.get("totp_code", "")).strip()
    ok, err = disable_totp(code)
    if not ok:
        ctx = {
            "admin": admin,
            "active_nav": "configuracoes",
            "totp": totp_status(),
            "totp_enabled": True,
            "setup_secret": "",
            "qr_data_url": "",
            "error": err,
            "success_msg": "",
        }
        return templates.TemplateResponse(
            request,
            "master/configuracoes/totp.html",
            template_context(request, **ctx),
            status_code=400,
        )
    request.session.pop("totp_setup_secret", None)
    clear_totp_session_verified(request)
    return RedirectResponse("/configuracoes/2fa?obrigatorio=1", status_code=303)
