"""API REST Express — sem dependência de PostgreSQL."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from app.clients.gateway_api import GatewayAPIError
from app.schemas.express import (
    ExpressConfirmRequest,
    ExpressConfirmResponse,
    ExpressStartRequest,
    ExpressStartResponse,
    ExpressVehicleSelectRequest,
    NetworkContextResponse,
)
from app.services import express_service
from app.services.gateway_service import fetch_network, is_hotel_like, resolve_contributor_ref

router = APIRouter(prefix="/express", tags=["express"])


@router.get("/network/{slug}/{codigo}", response_model=NetworkContextResponse)
async def get_network_context(slug: str, codigo: str, ref: str | None = None):
    try:
        network = await fetch_network(slug, codigo)
    except GatewayAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message) from e
    return NetworkContextResponse(
        network=network,
        is_hotel=is_hotel_like(network.get("type")),
        default_origin=network.get("default_origin", ""),
        contributor_ref=resolve_contributor_ref(network, ref),
    )


@router.post("/start", response_model=ExpressStartResponse)
async def start_express(data: ExpressStartRequest, request: Request):
    slug = data.slug or request.session.get("network_slug")
    codigo = data.codigo or request.session.get("network_codigo")
    if not slug or not codigo:
        raise HTTPException(status_code=400, detail="Rede não identificada.")

    try:
        network = await fetch_network(slug, codigo)
    except GatewayAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message) from e

    ref = data.contributor_ref or request.session.get("contributor_ref")
    origin = network.get("default_origin") if is_hotel_like(network.get("type")) and network.get("default_origin") else data.origin

    reservation, quote = await express_service.express_start(
        network=network,
        slug=slug,
        codigo=codigo,
        trip_type=data.trip_type,
        origin=origin,
        destination=data.destination,
        trip_date=data.trip_date,
        trip_time=data.trip_time,
        passenger_name=data.passenger_name,
        passenger_whatsapp=data.passenger_whatsapp,
        contributor_ref=ref,
        return_date=data.return_date,
        return_time=data.return_time,
        hourly_hours=data.hourly_hours,
    )
    request.session["reservation_id"] = reservation.id
    return ExpressStartResponse(
        reservation_id=reservation.id,
        quote_id=quote.get("quote_id"),
        redirect_url=f"/express/{reservation.id}/veiculos",
    )


@router.get("/{reservation_id}/vehicle-types")
async def list_vehicle_types(reservation_id: UUID):
    reservation = express_service.get_reservation_or_none(str(reservation_id))
    if not reservation:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    items = await express_service.express_list_vehicle_types(reservation)
    return {"items": items, "cidade": reservation.network_city or None}


@router.get("/{reservation_id}/vehicles")
async def list_vehicles(reservation_id: UUID, type: str = Query(..., min_length=2)):
    reservation = express_service.get_reservation_or_none(str(reservation_id))
    if not reservation:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    items = await express_service.express_list_vehicles(reservation, type)
    return {"items": items, "type": type}


@router.post("/{reservation_id}/vehicle")
async def pick_vehicle(reservation_id: UUID, data: ExpressVehicleSelectRequest, request: Request):
    reservation = express_service.get_reservation_or_none(str(reservation_id))
    if not reservation:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    express_service.express_select_vehicle(
        reservation,
        {
            "id": data.vehicle_id,
            "category": data.category,
            "name": data.name,
            "image_url": data.image_url,
            "price": data.price,
        },
    )
    return {"redirect_url": f"/express/{reservation_id}/resumo"}


@router.get("/{reservation_id}/summary")
async def summary_data(reservation_id: UUID):
    reservation = express_service.get_reservation_or_none(str(reservation_id))
    if not reservation:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    return {
        "code": reservation.code,
        "origin": reservation.origin,
        "destination": reservation.destination,
        "trip_date": reservation.trip_date.isoformat(),
        "trip_time": str(reservation.trip_time),
        "vehicle_name": reservation.vehicle_name,
        "total_amount": reservation.total_amount,
        "passenger_name": reservation.passenger_name,
        "passenger_whatsapp": reservation.passenger_whatsapp,
    }


@router.post("/{reservation_id}/confirm", response_model=ExpressConfirmResponse)
async def confirm_express(reservation_id: UUID, data: ExpressConfirmRequest, request: Request):
    if not data.lgpd_accepted:
        raise HTTPException(status_code=400, detail="Aceite LGPD obrigatório")

    reservation = express_service.get_reservation_or_none(str(reservation_id))
    if not reservation:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    slug = reservation.slug or request.session.get("network_slug")
    codigo = reservation.codigo or request.session.get("network_codigo")
    try:
        network = await fetch_network(slug, codigo)
    except GatewayAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message) from e

    try:
        reservation, result = await express_service.express_confirm(
            reservation, network, lgpd_accepted=True
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    wa = network.get("whatsapp_support", "")
    msg = f"Olá! Minha solicitação {reservation.code} foi confirmada."
    return ExpressConfirmResponse(
        reservation_code=reservation.code,
        redirect_url=f"/express/{reservation_id}/confirmado",
        whatsapp_url=express_service.whatsapp_url(wa, msg) if wa else None,
        message=result.get("message", "Sua solicitação foi enviada com sucesso."),
    )
