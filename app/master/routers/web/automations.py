"""Rotas web — Automacoes (webhooks seguros)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.automation_service import (
    create_automation,
    delete_automation,
    find_automation,
    list_automations,
    list_summary,
    toggle_automation,
    type_choices,
    update_domain,
)

router = APIRouter(prefix="/automacoes", tags=["master-automations"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


@router.get("")
async def list_page(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/automacoes/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="automacoes",
            automations=list_automations(runtime),
            summary=list_summary(runtime),
        ),
    )


@router.get("/nova")
async def create_form(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "master/automacoes/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="automacoes",
            type_choices=type_choices(),
            form={},
            error="",
        ),
    )


@router.post("/nova")
async def create_submit(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    item, errors = create_automation(runtime, form_data)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/automacoes/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="automacoes",
                type_choices=type_choices(),
                form=form_data,
                error="; ".join(errors),
            ),
            status_code=400,
        )
    return RedirectResponse(f"/automacoes/{item['token']}", status_code=303)


@router.get("/{token}")
async def detail_page(request: Request, token: str, saved: int = 0):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    item = find_automation(runtime, token)
    if not item:
        return RedirectResponse("/automacoes", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/automacoes/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="automacoes",
            automation=item,
            tests=item.get("tests") or [],
            saved=bool(saved),
            domain_error="",
        ),
    )


@router.post("/{token}/dominio")
async def save_domain(request: Request, token: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    item, errors = update_domain(runtime, token, form_data)
    if errors:
        current = find_automation(runtime, token) or {"token": token}
        return templates.TemplateResponse(
            request,
            "master/automacoes/detail.html",
            template_context(
                request,
                admin=admin,
                active_nav="automacoes",
                automation=current,
                tests=current.get("tests") or [],
                saved=False,
                domain_error="; ".join(errors),
            ),
            status_code=400,
        )
    return RedirectResponse(f"/automacoes/{token}?saved=1", status_code=303)


@router.post("/{token}/toggle")
async def toggle_status(request: Request, token: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    _item, errors = toggle_automation(runtime, token)
    if errors:
        return RedirectResponse("/automacoes", status_code=303)
    return RedirectResponse(f"/automacoes/{token}", status_code=303)


@router.post("/{token}/excluir")
async def delete_item(request: Request, token: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    delete_automation(runtime, token)
    return RedirectResponse("/automacoes", status_code=303)
