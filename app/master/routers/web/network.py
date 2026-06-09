"""Rotas web — Rede Comercial."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.network_service import (
    COMMISSION_STATUS_OPTIONS,
    commissions_summary,
    create_contributor,
    create_partner,
    dashboard_context,
    delete_contributor,
    find_contributor,
    find_partner,
    list_commissions,
    list_contributors,
    list_partners,
    partner_choices,
    partner_form_fields,
    update_contributor,
    update_partner,
    toggle_partner,
)

router = APIRouter(prefix="/rede", tags=["master-network"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


def _nav(active: str):
    return {
        "active_nav": "rede",
        "rede_tab": active,
    }


@router.get("")
async def rede_dashboard(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/rede/dashboard.html",
        template_context(request, admin=admin, kpis=dashboard_context(runtime), **_nav("dashboard")),
    )


@router.get("/parceiros")
async def partners_list(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/rede/parceiros/list.html",
        template_context(request, admin=admin, partners=list_partners(runtime), **_nav("parceiros")),
    )


@router.get("/parceiros/nova")
async def partner_create_form(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    fields = partner_form_fields()
    return templates.TemplateResponse(
        request,
        "master/rede/parceiros/form.html",
        template_context(
            request,
            admin=admin,
            partner=None,
            form={},
            error="",
            is_edit=False,
            fields=fields,
            **_nav("parceiros"),
        ),
    )


@router.post("/parceiros/nova")
async def partner_create_submit(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    item, errors = create_partner(runtime, form_data)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/rede/parceiros/form.html",
            template_context(
                request,
                admin=admin,
                partner=None,
                form=form_data,
                error="; ".join(errors),
                is_edit=False,
                fields=partner_form_fields(),
                **_nav("parceiros"),
            ),
            status_code=400,
        )
    return RedirectResponse(f"/rede/parceiros/{item['id']}", status_code=303)


@router.get("/parceiros/{partner_id}")
async def partner_detail(request: Request, partner_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    partner = find_partner(runtime, partner_id)
    if not partner:
        return RedirectResponse("/rede/parceiros", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/rede/parceiros/detail.html",
        template_context(
            request,
            admin=admin,
            partner=partner,
            contributors=list_contributors(runtime, partner_id=partner_id),
            **_nav("parceiros"),
        ),
    )


@router.get("/parceiros/{partner_id}/editar")
async def partner_edit_form(request: Request, partner_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    partner = find_partner(runtime, partner_id)
    if not partner:
        return RedirectResponse("/rede/parceiros", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/rede/parceiros/form.html",
        template_context(
            request,
            admin=admin,
            partner=partner,
            form=partner,
            error="",
            is_edit=True,
            fields=partner_form_fields(),
            **_nav("parceiros"),
        ),
    )


@router.post("/parceiros/{partner_id}/editar")
async def partner_edit_submit(request: Request, partner_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    item, errors = update_partner(runtime, partner_id, form_data)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/rede/parceiros/form.html",
            template_context(
                request,
                admin=admin,
                partner=find_partner(runtime, partner_id),
                form=form_data,
                error="; ".join(errors),
                is_edit=True,
                fields=partner_form_fields(),
                **_nav("parceiros"),
            ),
            status_code=400,
        )
    return RedirectResponse(f"/rede/parceiros/{item['id']}", status_code=303)


@router.post("/parceiros/{partner_id}/toggle")
async def partner_toggle(request: Request, partner_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    toggle_partner(runtime, partner_id)
    return RedirectResponse(f"/rede/parceiros/{partner_id}", status_code=303)


@router.get("/contribuidores")
async def contributors_list(request: Request, partner_id: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/rede/contribuidores/list.html",
        template_context(
            request,
            admin=admin,
            contributors=list_contributors(runtime, partner_id=partner_id),
            partner_choices=partner_choices(runtime),
            filter_partner_id=partner_id,
            **_nav("contribuidores"),
        ),
    )


@router.get("/contribuidores/nova")
async def contributor_create_form(request: Request, partner_id: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/rede/contribuidores/form.html",
        template_context(
            request,
            admin=admin,
            contributor=None,
            form={"partner_id": partner_id},
            error="",
            is_edit=False,
            partner_choices=partner_choices(runtime),
            **_nav("contribuidores"),
        ),
    )


@router.post("/contribuidores/nova")
async def contributor_create_submit(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    item, errors = create_contributor(runtime, form_data)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/rede/contribuidores/form.html",
            template_context(
                request,
                admin=admin,
                contributor=None,
                form=form_data,
                error="; ".join(errors),
                is_edit=False,
                partner_choices=partner_choices(runtime),
                **_nav("contribuidores"),
            ),
            status_code=400,
        )
    return RedirectResponse(f"/rede/contribuidores/{item['id']}/editar", status_code=303)


@router.get("/contribuidores/{contributor_id}/editar")
async def contributor_edit_form(request: Request, contributor_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    contributor, _partner = find_contributor(runtime, contributor_id)
    if not contributor:
        return RedirectResponse("/rede/contribuidores", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/rede/contribuidores/form.html",
        template_context(
            request,
            admin=admin,
            contributor=contributor,
            form=contributor,
            error="",
            is_edit=True,
            partner_choices=partner_choices(runtime),
            **_nav("contribuidores"),
        ),
    )


@router.post("/contribuidores/{contributor_id}/editar")
async def contributor_edit_submit(request: Request, contributor_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    item, errors = update_contributor(runtime, contributor_id, form_data)
    if errors:
        contributor, _ = find_contributor(runtime, contributor_id)
        return templates.TemplateResponse(
            request,
            "master/rede/contribuidores/form.html",
            template_context(
                request,
                admin=admin,
                contributor=contributor,
                form=form_data,
                error="; ".join(errors),
                is_edit=True,
                partner_choices=partner_choices(runtime),
                **_nav("contribuidores"),
            ),
            status_code=400,
        )
    return RedirectResponse(f"/rede/contribuidores/{item['id']}/editar", status_code=303)


@router.post("/contribuidores/{contributor_id}/excluir")
async def contributor_delete(request: Request, contributor_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    delete_contributor(runtime, contributor_id)
    return RedirectResponse("/rede/contribuidores", status_code=303)


@router.get("/comissoes")
async def commissions_list(request: Request, status: str = "", partner_id: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/rede/comissoes/list.html",
        template_context(
            request,
            admin=admin,
            commissions=list_commissions(runtime, status=status, partner_id=partner_id),
            summary=commissions_summary(runtime),
            partner_choices=partner_choices(runtime),
            filter_status=status,
            filter_partner_id=partner_id,
            status_options=COMMISSION_STATUS_OPTIONS,
            **_nav("comissoes"),
        ),
    )
