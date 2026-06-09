"""Rotas web — CRUD de leads de empresas."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.platform import COMPANY_LEAD_STATUSES, ORIGIN_SITE

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.company_lead_service import (
    BLOCK_STATUS,
    activate_company_lead,
    block_company_lead,
    create_company_lead,
    filter_options,
    find_company_lead_by_id,
    lead_display_name,
    lead_stats,
    linked_company,
    list_company_leads,
    list_summary,
    update_company_lead,
)
from ...validators.company_lead import map_service_error, validate_company_lead_form

router = APIRouter(prefix="/leads/empresas", tags=["master-company-leads"])


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
        "master/leads/empresas/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="leads_empresas",
            leads=list_company_leads(runtime, search=q, status=status),
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
        "master/leads/empresas/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="leads_empresas",
            status_options=COMPANY_LEAD_STATUSES,
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
    errors = validate_company_lead_form(form_data, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/leads/empresas/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="leads_empresas",
                status_options=COMPANY_LEAD_STATUSES,
                origin_default=ORIGIN_SITE,
                form=form_data,
                error="; ".join(errors),
            ),
            status_code=422,
        )
    item = create_company_lead(runtime, form_data)
    return RedirectResponse(f"/leads/empresas/{item['id']}?success=criado", status_code=303)


@router.get("/{lead_id}")
async def detail_page(request: Request, lead_id: str, success: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    item = find_company_lead_by_id(runtime, lead_id)
    if not item:
        return RedirectResponse("/leads/empresas", status_code=303)
    success_msg = {
        "criado": "Lead de empresa cadastrado com sucesso.",
        "editado": "Lead de empresa atualizado com sucesso.",
        "ativado": "Lead reativado.",
        "bloqueado": "Lead marcado como Perdido.",
    }.get(success, "")
    return templates.TemplateResponse(
        request,
        "master/leads/empresas/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="leads_empresas",
            item=item,
            item_name=lead_display_name(item),
            stats=lead_stats(runtime, item),
            company=linked_company(runtime, item),
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
    item = find_company_lead_by_id(runtime, lead_id)
    if not item:
        return RedirectResponse("/leads/empresas", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/leads/empresas/form_edit.html",
        template_context(
            request,
            admin=admin,
            active_nav="leads_empresas",
            item=item,
            item_name=lead_display_name(item),
            status_options=COMPANY_LEAD_STATUSES,
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
    item = find_company_lead_by_id(runtime, lead_id)
    if not item:
        return RedirectResponse("/leads/empresas", status_code=303)
    form_data = _form_dict(await request.form())
    errors = validate_company_lead_form(form_data, is_create=False)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/leads/empresas/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="leads_empresas",
                item=item,
                item_name=lead_display_name(item),
                status_options=COMPANY_LEAD_STATUSES,
                form={**item, **form_data},
                error="; ".join(errors),
            ),
            status_code=422,
        )
    try:
        update_company_lead(runtime, lead_id, form_data)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "master/leads/empresas/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="leads_empresas",
                item=item,
                item_name=lead_display_name(item),
                status_options=COMPANY_LEAD_STATUSES,
                form={**item, **form_data},
                error=map_service_error(str(exc)),
            ),
            status_code=422,
        )
    return RedirectResponse(f"/leads/empresas/{lead_id}?success=editado", status_code=303)


@router.post("/{lead_id}/bloquear")
async def block_submit(request: Request, lead_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        block_company_lead(runtime, lead_id)
    except ValueError:
        return RedirectResponse("/leads/empresas", status_code=303)
    return RedirectResponse(f"/leads/empresas/{lead_id}?success=bloqueado", status_code=303)


@router.post("/{lead_id}/ativar")
async def activate_submit(request: Request, lead_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        activate_company_lead(runtime, lead_id)
    except ValueError:
        return RedirectResponse("/leads/empresas", status_code=303)
    return RedirectResponse(f"/leads/empresas/{lead_id}?success=ativado", status_code=303)
