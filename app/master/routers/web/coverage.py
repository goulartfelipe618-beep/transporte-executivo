"""Rotas web — CRUD de abrangencia (pontos operacionais)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.geography import OPERATIONAL_POINT_STATUSES, OPERATIONAL_POINT_TYPES

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.coverage_service import (
    activate_coverage_point,
    block_coverage_point,
    create_coverage_point,
    filter_options,
    find_point_by_id,
    linked_drivers,
    linked_reservations,
    linked_vehicles,
    list_coverage_points,
    list_municipalities,
    list_states,
    list_summary,
    point_display_name,
    point_stats,
    update_coverage_point,
)
from ...validators.coverage import map_service_error, validate_coverage_form

router = APIRouter(prefix="/abrangencia", tags=["master-coverage"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


def _form_context(runtime, form, *, uf="", error=""):
    uf = str(uf or form.get("estado_uf", "")).upper().strip()
    cities = list_municipalities(uf) if uf else []
    return {
        "states": list_states(),
        "cities": cities,
        "selected_uf": uf,
        "point_types": OPERATIONAL_POINT_TYPES,
        "status_options": OPERATIONAL_POINT_STATUSES,
        "form": form,
        "error": error,
    }


@router.get("")
async def list_coverage_page(
    request: Request,
    q: str = "",
    tipo: str = "",
    status: str = "",
    uf: str = "",
):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    options = filter_options()
    return templates.TemplateResponse(
        request,
        "master/coverage/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="abrangencia",
            points=list_coverage_points(runtime, search=q, tipo=tipo, status=status, uf=uf),
            search=q,
            filter_tipo=tipo,
            filter_status=status,
            filter_uf=uf,
            filter_tipos=options["tipos"],
            filter_statuses=options["statuses"],
            filter_ufs=options["ufs"],
            summary=list_summary(runtime),
        ),
    )


@router.get("/nova")
async def create_form(request: Request, uf: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/coverage/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="abrangencia",
            **_form_context(runtime, {}, uf=uf),
        ),
    )


@router.post("/nova")
async def create_submit(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    errors = validate_coverage_form(form_data, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/coverage/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="abrangencia",
                **_form_context(runtime, form_data, uf=form_data.get("estado_uf", ""), error="; ".join(errors)),
            ),
            status_code=422,
        )
    point = create_coverage_point(runtime, form_data)
    return RedirectResponse(f"/abrangencia/{point['id']}?success=criado", status_code=303)


@router.get("/{point_id}")
async def detail_page(request: Request, point_id: str, success: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    point = find_point_by_id(runtime, point_id)
    if not point:
        return RedirectResponse("/abrangencia", status_code=303)
    success_msg = ""
    if success == "criado":
        success_msg = "Ponto operacional cadastrado com sucesso."
    elif success == "editado":
        success_msg = "Ponto operacional atualizado com sucesso."
    elif success == "ativado":
        success_msg = "Ponto operacional ativado."
    elif success == "bloqueado":
        success_msg = "Ponto operacional bloqueado."
    return templates.TemplateResponse(
        request,
        "master/coverage/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="abrangencia",
            point=point,
            point_name=point_display_name(point),
            stats=point_stats(runtime, point),
            drivers=linked_drivers(runtime, point),
            reservations=linked_reservations(runtime, point),
            vehicles=linked_vehicles(runtime, point),
            success_msg=success_msg,
        ),
    )


@router.get("/{point_id}/editar")
async def edit_form(request: Request, point_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    point = find_point_by_id(runtime, point_id)
    if not point:
        return RedirectResponse("/abrangencia", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/coverage/form_edit.html",
        template_context(
            request,
            admin=admin,
            active_nav="abrangencia",
            point=point,
            point_name=point_display_name(point),
            point_types=OPERATIONAL_POINT_TYPES,
            status_options=OPERATIONAL_POINT_STATUSES,
            form=point,
            error="",
        ),
    )


@router.post("/{point_id}/editar")
async def edit_submit(request: Request, point_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    point = find_point_by_id(runtime, point_id)
    if not point:
        return RedirectResponse("/abrangencia", status_code=303)
    form_data = _form_dict(await request.form())
    errors = validate_coverage_form(form_data, is_create=False)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/coverage/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="abrangencia",
                point=point,
                point_name=point_display_name(point),
                point_types=OPERATIONAL_POINT_TYPES,
                status_options=OPERATIONAL_POINT_STATUSES,
                form={**point, **form_data},
                error="; ".join(errors),
            ),
            status_code=422,
        )
    try:
        update_coverage_point(runtime, point_id, form_data)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "master/coverage/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="abrangencia",
                point=point,
                point_name=point_display_name(point),
                point_types=OPERATIONAL_POINT_TYPES,
                status_options=OPERATIONAL_POINT_STATUSES,
                form={**point, **form_data},
                error=map_service_error(str(exc)),
            ),
            status_code=422,
        )
    return RedirectResponse(f"/abrangencia/{point_id}?success=editado", status_code=303)


@router.post("/{point_id}/bloquear")
async def block_submit(request: Request, point_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        block_coverage_point(runtime, point_id)
    except ValueError:
        return RedirectResponse("/abrangencia", status_code=303)
    return RedirectResponse(f"/abrangencia/{point_id}?success=bloqueado", status_code=303)


@router.post("/{point_id}/ativar")
async def activate_submit(request: Request, point_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        activate_coverage_point(runtime, point_id)
    except ValueError:
        return RedirectResponse("/abrangencia", status_code=303)
    return RedirectResponse(f"/abrangencia/{point_id}?success=ativado", status_code=303)
