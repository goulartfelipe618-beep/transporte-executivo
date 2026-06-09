"""Rotas web — CRUD de solicitacoes de transporte."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.platform import ORIGIN_SITE, TRANSPORT_REQUEST_STATUSES

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.transport_request_service import (
    activate_transport_request,
    block_transport_request,
    create_transport_request,
    filter_options,
    find_request_by_id,
    linked_company,
    linked_driver,
    linked_reservation,
    linked_vehicle,
    list_summary,
    list_transport_requests,
    request_display_name,
    request_stats,
    update_transport_request,
)
from ...validators.transport_request import map_service_error, validate_transport_request_form

router = APIRouter(prefix="/solicitacoes", tags=["master-transport-requests"])


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
        "master/solicitacoes/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="solicitacoes",
            requests=list_transport_requests(runtime, search=q, status=status),
            search=q,
            filter_status=status,
            filter_statuses=options["statuses"],
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
        "master/solicitacoes/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="solicitacoes",
            status_options=TRANSPORT_REQUEST_STATUSES,
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
    errors = validate_transport_request_form(form_data, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/solicitacoes/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="solicitacoes",
                status_options=TRANSPORT_REQUEST_STATUSES,
                origin_default=ORIGIN_SITE,
                form=form_data,
                error="; ".join(errors),
            ),
            status_code=422,
        )
    item = create_transport_request(runtime, form_data)
    return RedirectResponse(f"/solicitacoes/{item['id']}?success=criado", status_code=303)


@router.get("/{request_id}")
async def detail_page(request: Request, request_id: str, success: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    item = find_request_by_id(runtime, request_id)
    if not item:
        return RedirectResponse("/solicitacoes", status_code=303)
    success_msg = {
        "criado": "Solicitacao cadastrada com sucesso.",
        "editado": "Solicitacao atualizada com sucesso.",
        "ativado": "Solicitacao ativada.",
        "bloqueado": "Solicitacao cancelada.",
    }.get(success, "")
    reservation = linked_reservation(runtime, item)
    return templates.TemplateResponse(
        request,
        "master/solicitacoes/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="solicitacoes",
            item=item,
            item_name=request_display_name(item),
            stats=request_stats(runtime, item),
            reservation=reservation,
            company=linked_company(runtime, item),
            driver=linked_driver(runtime, item),
            vehicle=linked_vehicle(runtime, item),
            success_msg=success_msg,
        ),
    )


@router.get("/{request_id}/editar")
async def edit_form(request: Request, request_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    item = find_request_by_id(runtime, request_id)
    if not item:
        return RedirectResponse("/solicitacoes", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/solicitacoes/form_edit.html",
        template_context(
            request,
            admin=admin,
            active_nav="solicitacoes",
            item=item,
            item_name=request_display_name(item),
            status_options=TRANSPORT_REQUEST_STATUSES,
            form=item,
            error="",
        ),
    )


@router.post("/{request_id}/editar")
async def edit_submit(request: Request, request_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    item = find_request_by_id(runtime, request_id)
    if not item:
        return RedirectResponse("/solicitacoes", status_code=303)
    form_data = _form_dict(await request.form())
    errors = validate_transport_request_form(form_data, is_create=False)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/solicitacoes/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="solicitacoes",
                item=item,
                item_name=request_display_name(item),
                status_options=TRANSPORT_REQUEST_STATUSES,
                form={**item, **form_data},
                error="; ".join(errors),
            ),
            status_code=422,
        )
    try:
        update_transport_request(runtime, request_id, form_data)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "master/solicitacoes/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="solicitacoes",
                item=item,
                item_name=request_display_name(item),
                status_options=TRANSPORT_REQUEST_STATUSES,
                form={**item, **form_data},
                error=map_service_error(str(exc)),
            ),
            status_code=422,
        )
    return RedirectResponse(f"/solicitacoes/{request_id}?success=editado", status_code=303)


@router.post("/{request_id}/bloquear")
async def block_submit(request: Request, request_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        block_transport_request(runtime, request_id)
    except ValueError:
        return RedirectResponse("/solicitacoes", status_code=303)
    return RedirectResponse(f"/solicitacoes/{request_id}?success=bloqueado", status_code=303)


@router.post("/{request_id}/ativar")
async def activate_submit(request: Request, request_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        activate_transport_request(runtime, request_id)
    except ValueError:
        return RedirectResponse("/solicitacoes", status_code=303)
    return RedirectResponse(f"/solicitacoes/{request_id}?success=ativado", status_code=303)
