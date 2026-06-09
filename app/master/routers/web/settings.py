"""Rotas web — Configuracoes do Sistema Master."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ...dependencies import resolve_admin_or_redirect, template_context, templates
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
