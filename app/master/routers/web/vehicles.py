"""Rotas web — CRUD de veiculos."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.vehicles_model import VEHICLE_TYPES

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.vehicle_service import (
    activate_vehicle,
    block_vehicle,
    create_vehicle,
    find_vehicle_by_id,
    linked_drivers,
    list_drivers_for_select,
    list_summary,
    list_vehicle_documents,
    list_vehicle_images,
    list_vehicles,
    update_vehicle,
    vehicle_display_name,
    vehicle_reservations,
    vehicle_stats,
)
from ...validators.vehicle import (
    COBRANCA_OPTIONS,
    COMBUSTIVEL_OPTIONS,
    IMAGE_FIELDS,
    PEDAGIO_OPTIONS,
    SIM_NAO_OPTIONS,
    STATUS_OPTIONS,
    validate_vehicle_form,
)

router = APIRouter(prefix="/veiculos", tags=["master-vehicles"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


@router.get("")
async def list_vehicles_page(request: Request, q: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/vehicles/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="veiculos",
            vehicles=list_vehicles(runtime, search=q),
            search=q,
            summary=list_summary(runtime),
        ),
    )


@router.get("/novo")
async def create_form(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/vehicles/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="veiculos",
            vehicle_types=VEHICLE_TYPES,
            status_options=STATUS_OPTIONS,
            combustivel_options=COMBUSTIVEL_OPTIONS,
            cobranca_options=COBRANCA_OPTIONS,
            pedagio_options=PEDAGIO_OPTIONS,
            sim_nao_options=SIM_NAO_OPTIONS,
            image_fields=IMAGE_FIELDS,
            drivers=list_drivers_for_select(runtime),
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
    errors = validate_vehicle_form(form_data, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/vehicles/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="veiculos",
                vehicle_types=VEHICLE_TYPES,
                status_options=STATUS_OPTIONS,
                combustivel_options=COMBUSTIVEL_OPTIONS,
                cobranca_options=COBRANCA_OPTIONS,
                pedagio_options=PEDAGIO_OPTIONS,
                sim_nao_options=SIM_NAO_OPTIONS,
                image_fields=IMAGE_FIELDS,
                drivers=list_drivers_for_select(runtime),
                form=form_data,
                error=" ".join(errors),
            ),
            status_code=400,
        )
    vehicle = create_vehicle(runtime, form_data)
    return RedirectResponse(f"/veiculos/{vehicle.get('id')}?success=Veiculo+cadastrado", status_code=303)


@router.get("/{vehicle_id}")
async def vehicle_detail(request: Request, vehicle_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    vehicle = find_vehicle_by_id(runtime, vehicle_id)
    if not vehicle:
        return RedirectResponse("/veiculos", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/vehicles/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="veiculos",
            vehicle=vehicle,
            vehicle_name=vehicle_display_name(vehicle),
            stats=vehicle_stats(runtime, vehicle),
            images=list_vehicle_images(vehicle),
            documents=list_vehicle_documents(vehicle),
            drivers=linked_drivers(runtime, vehicle),
            reservations=vehicle_reservations(runtime, vehicle)[:30],
            success_msg=request.query_params.get("success", ""),
        ),
    )


@router.get("/{vehicle_id}/editar")
async def edit_form(request: Request, vehicle_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    vehicle = find_vehicle_by_id(runtime, vehicle_id)
    if not vehicle:
        return RedirectResponse("/veiculos", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/vehicles/form_edit.html",
        template_context(
            request,
            admin=admin,
            active_nav="veiculos",
            vehicle=vehicle,
            vehicle_types=VEHICLE_TYPES,
            status_options=STATUS_OPTIONS,
            combustivel_options=COMBUSTIVEL_OPTIONS,
            cobranca_options=COBRANCA_OPTIONS,
            pedagio_options=PEDAGIO_OPTIONS,
            sim_nao_options=SIM_NAO_OPTIONS,
            image_fields=IMAGE_FIELDS,
            drivers=list_drivers_for_select(runtime),
            error="",
        ),
    )


@router.post("/{vehicle_id}/editar")
async def edit_submit(request: Request, vehicle_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    vehicle = find_vehicle_by_id(runtime, vehicle_id)
    if not vehicle:
        return RedirectResponse("/veiculos", status_code=303)
    form_data = _form_dict(await request.form())
    errors = validate_vehicle_form(form_data)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/vehicles/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="veiculos",
                vehicle=vehicle,
                vehicle_types=VEHICLE_TYPES,
                status_options=STATUS_OPTIONS,
                combustivel_options=COMBUSTIVEL_OPTIONS,
                cobranca_options=COBRANCA_OPTIONS,
                pedagio_options=PEDAGIO_OPTIONS,
                sim_nao_options=SIM_NAO_OPTIONS,
                image_fields=IMAGE_FIELDS,
                drivers=list_drivers_for_select(runtime),
                error=" ".join(errors),
            ),
            status_code=400,
        )
    try:
        vehicle = update_vehicle(runtime, vehicle_id, form_data)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "master/vehicles/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="veiculos",
                vehicle=vehicle,
                vehicle_types=VEHICLE_TYPES,
                status_options=STATUS_OPTIONS,
                combustivel_options=COMBUSTIVEL_OPTIONS,
                cobranca_options=COBRANCA_OPTIONS,
                pedagio_options=PEDAGIO_OPTIONS,
                sim_nao_options=SIM_NAO_OPTIONS,
                image_fields=IMAGE_FIELDS,
                drivers=list_drivers_for_select(runtime),
                error=str(exc),
            ),
            status_code=400,
        )
    return RedirectResponse(f"/veiculos/{vehicle.get('id')}?success=Veiculo+atualizado", status_code=303)


@router.post("/{vehicle_id}/bloquear")
async def block_submit(request: Request, vehicle_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        block_vehicle(runtime, vehicle_id)
    except ValueError:
        pass
    return RedirectResponse("/veiculos", status_code=303)


@router.post("/{vehicle_id}/ativar")
async def activate_submit(request: Request, vehicle_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        activate_vehicle(runtime, vehicle_id)
    except ValueError:
        pass
    return RedirectResponse(f"/veiculos/{vehicle_id}?success=Veiculo+ativado", status_code=303)
