"""Rotas web — CRUD de reservas."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.address_po_service import operational_point_options
from ...services.reservation_service import (
    UNASSIGNED_DRIVER,
    create_reservation,
    delete_reservation,
    filter_reservations,
    find_reservation,
    generate_pdf_bytes,
    pdf_filename,
    registered_clients,
    registered_drivers,
    update_reservation,
)

router = APIRouter(prefix="/reservas", tags=["master-reservations"])

PDF_VIAS = ("cliente", "motorista", "loja")
TRIP_TYPES = ("Somente Ida", "Ida e Volta", "Por Hora")
STATUS_OPTIONS = ("Pendente", "Confirmada", "Concluida", "Cancelada")


@router.get("")
async def list_reservations(
    request: Request,
    date_from: str = "",
    date_to: str = "",
    estado: str = "",
    motorista: str = "",
    search: str = "",
):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "estado": estado,
        "motorista": motorista,
        "search": search,
    }
    items = filter_reservations(runtime, filters)
    return templates.TemplateResponse(
        request,
        "master/reservations/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="reservas",
            reservations=items,
            filters=filters,
            total=len(getattr(runtime, "reservations", []) or []),
        ),
    )


@router.get("/nova")
async def create_form(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/reservations/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="reservas",
            clients=registered_clients(runtime),
            drivers=[UNASSIGNED_DRIVER] + registered_drivers(runtime),
            po_options=operational_point_options(runtime),
            trip_types=TRIP_TYPES,
            status_options=STATUS_OPTIONS,
            form={},
            error="",
            payable_notices=[],
        ),
    )


@router.post("/nova")
async def create_submit(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form = await request.form()
    form_data = {key: form.get(key, "") for key in form.keys()}
    created, error, notices = create_reservation(runtime, form_data)
    if error:
        return templates.TemplateResponse(
            request,
            "master/reservations/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="reservas",
                clients=registered_clients(runtime),
                drivers=[UNASSIGNED_DRIVER] + registered_drivers(runtime),
                po_options=operational_point_options(runtime),
                trip_types=TRIP_TYPES,
                status_options=STATUS_OPTIONS,
                form=form_data,
                error=error,
                payable_notices=[],
            ),
            status_code=400,
        )
    first = created[0] if created else None
    if first:
        numero = quote(str(first.get("numero", "")).lstrip("#"), safe="")
        url = f"/reservas/{numero}"
        if notices:
            url += "?payable=1"
        return RedirectResponse(url, status_code=303)
    return RedirectResponse("/reservas", status_code=303)


@router.get("/{numero}")
async def detail_reservation(request: Request, numero: str, payable: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    reservation = find_reservation(runtime, numero)
    if not reservation:
        return RedirectResponse("/reservas", status_code=303)
    show_payable = payable == "1"
    return templates.TemplateResponse(
        request,
        "master/reservations/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="reservas",
            reservation=reservation,
            pdf_vias=PDF_VIAS,
            show_payable_notice=show_payable,
        ),
    )


@router.get("/{numero}/editar")
async def edit_form(request: Request, numero: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    reservation = find_reservation(runtime, numero)
    if not reservation:
        return RedirectResponse("/reservas", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/reservations/form_edit.html",
        template_context(
            request,
            admin=admin,
            active_nav="reservas",
            reservation=reservation,
            status_options=STATUS_OPTIONS,
            error="",
        ),
    )


@router.post("/{numero}/editar")
async def edit_submit(request: Request, numero: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form = await request.form()
    form_data = {key: form.get(key, "") for key in form.keys()}
    ok, error = update_reservation(runtime, numero, form_data)
    reservation = find_reservation(runtime, numero)
    if not ok:
        return templates.TemplateResponse(
            request,
            "master/reservations/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="reservas",
                reservation=reservation or {"numero": numero},
                status_options=STATUS_OPTIONS,
                error=error,
            ),
            status_code=400,
        )
    return RedirectResponse(f"/reservas/{quote(str(numero).lstrip('#'), safe='')}", status_code=303)


@router.post("/{numero}/excluir")
async def delete_submit(request: Request, numero: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    delete_reservation(runtime, numero)
    return RedirectResponse("/reservas", status_code=303)


@router.get("/{numero}/pdf/{via}")
async def download_pdf(request: Request, numero: str, via: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    reservation = find_reservation(runtime, numero)
    if not reservation:
        return RedirectResponse("/reservas", status_code=303)
    via = via.lower()
    if via not in PDF_VIAS:
        via = "loja"
    content = generate_pdf_bytes(reservation, runtime, via)
    filename = pdf_filename(reservation, via)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
