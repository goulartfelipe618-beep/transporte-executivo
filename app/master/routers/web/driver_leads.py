"""Rotas web — CRUD de leads de motoristas."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.platform import DRIVER_LEAD_STATUSES, ORIGIN_SITE

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.driver_lead_service import (
    BLOCK_STATUS,
    activate_driver_lead,
    block_driver_lead,
    create_driver_lead,
    filter_options,
    find_driver_lead_by_id,
    lead_display_name,
    lead_stats,
    linked_driver,
    list_driver_leads,
    list_summary,
    update_driver_lead,
)
from ...validators.driver_lead import map_service_error, validate_driver_lead_form

router = APIRouter(prefix="/leads/motoristas", tags=["master-driver-leads"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


@router.get("")
async def list_page(request: Request, q: str = "", status: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    options = filter_options()
    return templates.TemplateResponse(
        request,
        "master/leads/motoristas/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="leads_motoristas",
            leads=list_driver_leads(runtime, search=q, status=status),
            search=q,
            filter_status=status,
            filter_statuses=options["statuses"],
            summary=list_summary(runtime),
            block_status=BLOCK_STATUS,
        ),
    )


@router.get("/nova")
async def create_form(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "master/leads/motoristas/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="leads_motoristas",
            status_options=DRIVER_LEAD_STATUSES,
            origin_default=ORIGIN_SITE,
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
    errors = validate_driver_lead_form(form_data, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/leads/motoristas/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="leads_motoristas",
                status_options=DRIVER_LEAD_STATUSES,
                origin_default=ORIGIN_SITE,
                form=form_data,
                error="; ".join(errors),
            ),
            status_code=422,
        )
    item = create_driver_lead(runtime, form_data)
    return RedirectResponse(f"/leads/motoristas/{item['id']}?success=criado", status_code=303)


@router.get("/{lead_id}")
async def detail_page(request: Request, lead_id: str, success: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    item = find_driver_lead_by_id(runtime, lead_id)
    if not item:
        return RedirectResponse("/leads/motoristas", status_code=303)
    success_msg = {
        "criado": "Lead de motorista cadastrado com sucesso.",
        "editado": "Lead de motorista atualizado com sucesso.",
        "ativado": "Lead reativado.",
        "bloqueado": "Lead marcado como Reprovado.",
    }.get(success, "")
    return templates.TemplateResponse(
        request,
        "master/leads/motoristas/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="leads_motoristas",
            item=item,
            item_name=lead_display_name(item),
            stats=lead_stats(runtime, item),
            driver=linked_driver(runtime, item),
            block_status=BLOCK_STATUS,
            success_msg=success_msg,
        ),
    )


@router.get("/{lead_id}/editar")
async def edit_form(request: Request, lead_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    item = find_driver_lead_by_id(runtime, lead_id)
    if not item:
        return RedirectResponse("/leads/motoristas", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/leads/motoristas/form_edit.html",
        template_context(
            request,
            admin=admin,
            active_nav="leads_motoristas",
            item=item,
            item_name=lead_display_name(item),
            status_options=DRIVER_LEAD_STATUSES,
            form=item,
            error="",
        ),
    )


@router.post("/{lead_id}/editar")
async def edit_submit(request: Request, lead_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    item = find_driver_lead_by_id(runtime, lead_id)
    if not item:
        return RedirectResponse("/leads/motoristas", status_code=303)
    form_data = _form_dict(await request.form())
    errors = validate_driver_lead_form(form_data, is_create=False)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/leads/motoristas/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="leads_motoristas",
                item=item,
                item_name=lead_display_name(item),
                status_options=DRIVER_LEAD_STATUSES,
                form={**item, **form_data},
                error="; ".join(errors),
            ),
            status_code=422,
        )
    try:
        update_driver_lead(runtime, lead_id, form_data)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "master/leads/motoristas/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="leads_motoristas",
                item=item,
                item_name=lead_display_name(item),
                status_options=DRIVER_LEAD_STATUSES,
                form={**item, **form_data},
                error=map_service_error(str(exc)),
            ),
            status_code=422,
        )
    return RedirectResponse(f"/leads/motoristas/{lead_id}?success=editado", status_code=303)


@router.post("/{lead_id}/bloquear")
async def block_submit(request: Request, lead_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        block_driver_lead(runtime, lead_id)
    except ValueError:
        return RedirectResponse("/leads/motoristas", status_code=303)
    return RedirectResponse(f"/leads/motoristas/{lead_id}?success=bloqueado", status_code=303)


@router.post("/{lead_id}/ativar")
async def activate_submit(request: Request, lead_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        activate_driver_lead(runtime, lead_id)
    except ValueError:
        return RedirectResponse("/leads/motoristas", status_code=303)
    return RedirectResponse(f"/leads/motoristas/{lead_id}?success=ativado", status_code=303)
