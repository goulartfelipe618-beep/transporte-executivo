"""Rotas web — CRUD de reservas."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.delete_guard import delete_confirm_response, verify_delete_confirmation
from ...services.address_po_service import operational_point_options
from ...services.client_service import booking_customer_options
from ...services.reservation_service import (
    UNASSIGNED_DRIVER,
    create_reservation,
    delete_reservation,
    filter_reservations,
    find_reservation,
    generate_pdf_bytes,
    pdf_filename,
    registered_drivers,
    reservation_to_form_dict,
    update_reservation,
)

router = APIRouter(prefix="/reservas", tags=["master-reservations"])

PDF_VIAS = ("cliente", "motorista", "loja")
TRIP_TYPES = ("Somente Ida", "Ida e Volta", "Por Hora")
STATUS_OPTIONS = ("Pendente", "Confirmada", "Concluida", "Cancelada")


def _reservation_form_context(
    request,
    admin,
    runtime,
    form,
    *,
    edit_numero: str = "",
    error: str = "",
    payable_notices=None,
):
    numero_slug = str(edit_numero or "").lstrip("#")
    is_edit = bool(numero_slug)
    return template_context(
        request,
        admin=admin,
        active_nav="reservas",
        booking_customers=booking_customer_options(runtime),
        drivers=[UNASSIGNED_DRIVER] + registered_drivers(runtime),
        po_options=operational_point_options(runtime),
        trip_types=TRIP_TYPES,
        status_options=STATUS_OPTIONS,
        form=form,
        error=error,
        payable_notices=payable_notices or [],
        page_heading="Editar Reserva" if is_edit else "Criar Nova Reserva",
        page_subtitle=(
            f"{edit_numero} — dados pre-preenchidos para alteracao."
            if is_edit
            else "Preencha os dados para criar uma nova reserva manual."
        ),
        form_action=f"/reservas/{numero_slug}/editar" if is_edit else "/reservas/nova",
        submit_label="Salvar alteracoes" if is_edit else "Criar Reserva",
        cancel_href=f"/reservas/{numero_slug}" if is_edit else "/reservas",
    )


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
        "master/reservations/form.html",
        _reservation_form_context(request, admin, runtime, {}),
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
            "master/reservations/form.html",
            _reservation_form_context(request, admin, runtime, form_data, error=error),
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
    form_data = reservation_to_form_dict(runtime, reservation)
    return templates.TemplateResponse(
        request,
        "master/reservations/form.html",
        _reservation_form_context(
            request,
            admin,
            runtime,
            form_data,
            edit_numero=reservation.get("numero", numero),
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
        base = reservation_to_form_dict(runtime, reservation) if reservation else {}
        merged = {**base, **form_data}
        return templates.TemplateResponse(
            request,
            "master/reservations/form.html",
            _reservation_form_context(
                request,
                admin,
                runtime,
                merged,
                edit_numero=(reservation or {}).get("numero", numero),
                error=error,
            ),
            status_code=400,
        )
    return RedirectResponse(f"/reservas/{quote(str(numero).lstrip('#'), safe='')}", status_code=303)


@router.get("/{numero}/excluir")
async def delete_form(request: Request, numero: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    reservation = find_reservation(runtime, numero)
    if not reservation:
        return RedirectResponse("/reservas", status_code=303)
    numero_slug = quote(str(numero).lstrip("#"), safe="")
    entity_id = str(reservation.get("numero", numero))
    label = f"{reservation.get('cliente', 'Reserva')} · {entity_id}"
    return delete_confirm_response(
        request,
        admin,
        active_nav="reservas",
        entity_title="Excluir reserva",
        entity_name=label,
        entity_id=entity_id,
        cancel_url=f"/reservas/{numero_slug}",
        post_url=f"/reservas/{numero_slug}/excluir",
        warning_message="Esta acao e irreversivel. A reserva e registros financeiros vinculados serao removidos.",
    )


@router.post("/{numero}/excluir")
async def delete_submit(request: Request, numero: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    reservation = find_reservation(runtime, numero)
    if not reservation:
        return RedirectResponse("/reservas", status_code=303)

    form_data = {key: form.get(key, "") for key in (await request.form()).keys()}
    numero_slug = quote(str(numero).lstrip("#"), safe="")
    entity_id = str(reservation.get("numero", numero))
    label = f"{reservation.get('cliente', 'Reserva')} · {entity_id}"
    ok, err = verify_delete_confirmation(form_data, entity_id)
    if not ok:
        return delete_confirm_response(
            request,
            admin,
            active_nav="reservas",
            entity_title="Excluir reserva",
            entity_name=label,
            entity_id=entity_id,
            cancel_url=f"/reservas/{numero_slug}",
            post_url=f"/reservas/{numero_slug}/excluir",
            warning_message="Esta acao e irreversivel. A reserva e registros financeiros vinculados serao removidos.",
            error=err,
            status_code=400,
        )
    delete_reservation(runtime, numero)
    return RedirectResponse("/reservas?success=Reserva+excluida", status_code=303)


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
