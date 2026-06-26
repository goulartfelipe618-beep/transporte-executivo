"""Rotas web — CRUD de clientes pessoa fisica."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.client_service import (
    client_display_name,
    client_document,
    create_client,
    delete_client,
    find_physical_client,
    list_physical_clients,
    list_summary,
    update_client,
)
from ...validators.client import validate_client_form

router = APIRouter(prefix="/clientes", tags=["master-clients"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


@router.get("")
async def list_clients(request: Request, q: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/clientes/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="clientes",
            clients=list_physical_clients(runtime, search=q),
            search=q,
            summary=list_summary(runtime),
        ),
    )


@router.get("/novo")
async def create_form(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "master/clientes/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="clientes",
            form={},
            error="",
        ),
    )


@router.post("/novo")
async def create_submit(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    errors = validate_client_form(form_data, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/clientes/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="clientes",
                form=form_data,
                error=" ".join(errors),
            ),
            status_code=400,
        )
    client = create_client(runtime, form_data)
    return RedirectResponse(f"/clientes/{client.get('id')}", status_code=303)


@router.get("/{client_id}")
async def detail_client(request: Request, client_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    client = find_physical_client(runtime, client_id)
    if not client:
        return RedirectResponse("/clientes", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/clientes/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="clientes",
            client=client,
            display_name=client_display_name(client),
            document=client_document(client),
        ),
    )


@router.get("/{client_id}/editar")
async def edit_form(request: Request, client_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    client = find_physical_client(runtime, client_id)
    if not client:
        return RedirectResponse("/clientes", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/clientes/form_edit.html",
        template_context(
            request,
            admin=admin,
            active_nav="clientes",
            client=client,
            error="",
        ),
    )


@router.post("/{client_id}/editar")
async def edit_submit(request: Request, client_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    errors = validate_client_form(form_data, is_create=False)
    client = find_physical_client(runtime, client_id)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/clientes/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="clientes",
                client=client or {"id": client_id},
                error=" ".join(errors),
            ),
            status_code=400,
        )
    updated, error = update_client(runtime, client_id, form_data)
    if error:
        return templates.TemplateResponse(
            request,
            "master/clientes/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="clientes",
                client=updated or client or {"id": client_id},
                error=error,
            ),
            status_code=400,
        )
    return RedirectResponse(f"/clientes/{client_id}", status_code=303)


@router.post("/{client_id}/excluir")
async def delete_submit(request: Request, client_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    delete_client(runtime, client_id)
    return RedirectResponse("/clientes", status_code=303)
