"""Rotas web — CRUD de empresas corporativas."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.company_model import COMPANY_STATUSES, COMPANY_USER_PROFILES, COMPANY_USER_STATUSES
from app.portal_auth import COMPANY_PERMISSIONS

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.company_service import (
    block_company,
    company_display_name,
    company_document,
    company_stats,
    create_company,
    find_company_by_id,
    list_corporate_companies,
    list_summary,
    portal_info,
    update_company,
)
from ...services.company_user_service import create_user, deactivate_user, find_user, list_users, update_user
from ...validators.company import validate_company_form, validate_company_user_form

router = APIRouter(prefix="/empresas", tags=["master-companies"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


@router.get("")
async def list_companies(request: Request, q: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/companies/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="empresas",
            companies=list_corporate_companies(runtime, search=q),
            search=q,
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
        "master/companies/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="empresas",
            company_statuses=COMPANY_STATUSES,
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
    errors = validate_company_form(form_data, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/companies/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="empresas",
                company_statuses=COMPANY_STATUSES,
                form=form_data,
                error=" ".join(errors),
            ),
            status_code=400,
        )
    company, _admin_user, temp_password = create_company(runtime, form_data)
    url = f"/empresas/{company.get('id')}"
    if temp_password:
        url += f"?temp_password={temp_password}"
    return RedirectResponse(url, status_code=303)


@router.get("/{company_id}")
async def company_detail(request: Request, company_id: str, temp_password: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    company = find_company_by_id(runtime, company_id)
    if not company:
        return RedirectResponse("/empresas", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/companies/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="empresas",
            company=company,
            company_name=company_display_name(company),
            company_doc=company_document(company),
            users=list_users(runtime, company_id),
            stats=company_stats(runtime, company),
            portal=portal_info(company),
            permissions=COMPANY_PERMISSIONS,
            temp_password=temp_password,
            success_msg=request.query_params.get("success", ""),
        ),
    )


@router.get("/{company_id}/editar")
async def edit_form(request: Request, company_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    company = find_company_by_id(runtime, company_id)
    if not company:
        return RedirectResponse("/empresas", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/companies/form_edit.html",
        template_context(
            request,
            admin=admin,
            active_nav="empresas",
            company=company,
            company_statuses=COMPANY_STATUSES,
            users=list_users(runtime, company_id),
            portal=portal_info(company),
            error="",
        ),
    )


@router.post("/{company_id}/editar")
async def edit_submit(request: Request, company_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    company = find_company_by_id(runtime, company_id)
    if not company:
        return RedirectResponse("/empresas", status_code=303)
    errors = validate_company_form(form_data)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/companies/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="empresas",
                company=company,
                company_statuses=COMPANY_STATUSES,
                users=list_users(runtime, company_id),
                portal=portal_info(company),
                error=" ".join(errors),
            ),
            status_code=400,
        )
    try:
        company, _admin_user, temp_password = update_company(runtime, company_id, form_data)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "master/companies/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="empresas",
                company=company,
                company_statuses=COMPANY_STATUSES,
                users=list_users(runtime, company_id),
                portal=portal_info(company),
                error=str(exc),
            ),
            status_code=400,
        )
    url = f"/empresas/{company.get('id')}?success=Empresa+atualizada"
    if temp_password:
        url += f"&temp_password={temp_password}"
    return RedirectResponse(url, status_code=303)


@router.post("/{company_id}/bloquear")
async def block_submit(request: Request, company_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        block_company(runtime, company_id)
    except ValueError:
        pass
    return RedirectResponse("/empresas", status_code=303)


@router.get("/{company_id}/usuarios/nova")
async def user_create_form(request: Request, company_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    company = find_company_by_id(runtime, company_id)
    if not company:
        return RedirectResponse("/empresas", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/companies/user_form.html",
        template_context(
            request,
            admin=admin,
            active_nav="empresas",
            company=company,
            user_profiles=COMPANY_USER_PROFILES,
            user_statuses=COMPANY_USER_STATUSES,
            user=None,
            form={},
            error="",
            is_create=True,
        ),
    )


@router.post("/{company_id}/usuarios/nova")
async def user_create_submit(request: Request, company_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    company = find_company_by_id(runtime, company_id)
    if not company:
        return RedirectResponse("/empresas", status_code=303)
    form_data = _form_dict(await request.form())
    errors = validate_company_user_form(form_data, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/companies/user_form.html",
            template_context(
                request,
                admin=admin,
                active_nav="empresas",
                company=company,
                user_profiles=COMPANY_USER_PROFILES,
                user_statuses=COMPANY_USER_STATUSES,
                user=None,
                form=form_data,
                error=" ".join(errors),
                is_create=True,
            ),
            status_code=400,
        )
    try:
        _saved, temp_password = create_user(runtime, company_id, form_data, actor=admin, must_change_password=True)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "master/companies/user_form.html",
            template_context(
                request,
                admin=admin,
                active_nav="empresas",
                company=company,
                user_profiles=COMPANY_USER_PROFILES,
                user_statuses=COMPANY_USER_STATUSES,
                user=None,
                form=form_data,
                error=str(exc),
                is_create=True,
            ),
            status_code=400,
        )
    url = f"/empresas/{company_id}?success=Usuario+cadastrado"
    if temp_password:
        url += f"&temp_password={temp_password}"
    return RedirectResponse(url, status_code=303)


@router.get("/{company_id}/usuarios/{user_id}/editar")
async def user_edit_form(request: Request, company_id: str, user_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    company = find_company_by_id(runtime, company_id)
    user = find_user(runtime, company_id, user_id)
    if not company or not user:
        return RedirectResponse(f"/empresas/{company_id}", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/companies/user_form.html",
        template_context(
            request,
            admin=admin,
            active_nav="empresas",
            company=company,
            user_profiles=COMPANY_USER_PROFILES,
            user_statuses=COMPANY_USER_STATUSES,
            user=user,
            form=user,
            error="",
            is_create=False,
        ),
    )


@router.post("/{company_id}/usuarios/{user_id}/editar")
async def user_edit_submit(request: Request, company_id: str, user_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    company = find_company_by_id(runtime, company_id)
    user = find_user(runtime, company_id, user_id)
    if not company or not user:
        return RedirectResponse(f"/empresas/{company_id}", status_code=303)
    form_data = _form_dict(await request.form())
    errors = validate_company_user_form(form_data, is_create=False)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/companies/user_form.html",
            template_context(
                request,
                admin=admin,
                active_nav="empresas",
                company=company,
                user_profiles=COMPANY_USER_PROFILES,
                user_statuses=COMPANY_USER_STATUSES,
                user=user,
                form=form_data,
                error=" ".join(errors),
                is_create=False,
            ),
            status_code=400,
        )
    try:
        update_user(runtime, company_id, user_id, form_data, actor=admin)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "master/companies/user_form.html",
            template_context(
                request,
                admin=admin,
                active_nav="empresas",
                company=company,
                user_profiles=COMPANY_USER_PROFILES,
                user_statuses=COMPANY_USER_STATUSES,
                user=user,
                form=form_data,
                error=str(exc),
                is_create=False,
            ),
            status_code=400,
        )
    return RedirectResponse(f"/empresas/{company_id}?success=Usuario+atualizado", status_code=303)


@router.post("/{company_id}/usuarios/{user_id}/excluir")
async def user_delete_submit(request: Request, company_id: str, user_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        deactivate_user(runtime, company_id, user_id, actor=admin)
    except ValueError:
        pass
    return RedirectResponse(f"/empresas/{company_id}", status_code=303)
