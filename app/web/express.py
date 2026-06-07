"""Rotas HTML Express — mobile-first, sem PostgreSQL."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.services import express_service
from app.services.document_service import generate_qr_code_png
from app.services.gateway_service import is_hotel_like

router = APIRouter(prefix="/express", tags=["express-web"])
templates = Jinja2Templates(directory="app/templates")


def _ctx(request: Request, step: int, **extra):
    network = request.session.get("network") or {}
    colors = network.get("colors") or {}
    return {
        "step": step,
        "flow": "express",
        "network": network,
        "is_hotel": is_hotel_like(network.get("type")),
        "default_origin": network.get("default_origin", ""),
        "contributor_ref": request.session.get("contributor_ref"),
        "branding": colors,
        "slug": request.session.get("network_slug", ""),
        "codigo": request.session.get("network_codigo", ""),
        **extra,
    }


@router.get("/inicio", response_class=HTMLResponse)
async def express_generic_start(request: Request):
    return templates.TemplateResponse(request, "express/step1.html", _ctx(request, 1))


@router.get("/{reservation_id}/veiculos", response_class=HTMLResponse)
async def express_vehicles_page(reservation_id: UUID, request: Request):
    reservation = express_service.get_reservation_or_none(str(reservation_id))
    if not reservation:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    return templates.TemplateResponse(
        request,
        "express/step2.html",
        _ctx(request, 2, reservation_id=str(reservation_id)),
    )


@router.get("/{reservation_id}/resumo", response_class=HTMLResponse)
async def express_summary_page(reservation_id: UUID, request: Request):
    reservation = express_service.get_reservation_or_none(str(reservation_id))
    if not reservation:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    return templates.TemplateResponse(
        request,
        "express/step3.html",
        _ctx(
            request,
            3,
            reservation_id=str(reservation_id),
            reservation=reservation,
            passenger_name=reservation.passenger_name,
            passenger_whatsapp=reservation.passenger_whatsapp,
        ),
    )


@router.get("/{reservation_id}/confirmado", response_class=HTMLResponse)
async def express_done_page(reservation_id: UUID, request: Request):
    reservation = express_service.get_reservation_or_none(str(reservation_id))
    if not reservation:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    network = request.session.get("network") or {}
    wa = network.get("whatsapp_support", "")
    msg = f"Olá! Minha solicitação {reservation.code} foi confirmada."
    wa_link = express_service.whatsapp_url(wa, msg) if wa else None
    return templates.TemplateResponse(
        request,
        "express/done.html",
        _ctx(
            request,
            4,
            reservation=reservation,
            reservation_id=str(reservation_id),
            whatsapp_url=wa_link,
            passenger_whatsapp=reservation.passenger_whatsapp,
        ),
    )


@router.get("/{reservation_id}/qr")
async def express_qr(reservation_id: UUID):
    reservation = express_service.get_reservation_or_none(str(reservation_id))
    if not reservation:
        raise HTTPException(status_code=404)
    from app.config import get_settings

    settings = get_settings()
    data = f"{settings.base_url}/express/{reservation_id}/confirmado?code={reservation.code}"
    return Response(content=generate_qr_code_png(data), media_type="image/png")
