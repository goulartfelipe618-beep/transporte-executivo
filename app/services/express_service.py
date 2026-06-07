"""Orquestração Express — Gateway + catálogo por cidade/tipo."""

from datetime import date, time
from typing import Any, Optional
from urllib.parse import quote

from app.clients.gateway_api import GatewayAPIClient
from app.domain.vehicle_types import normalize_vehicle_type
from app.security.sanitize import sanitize_phone, sanitize_text
from app.services.express_store import ExpressReservation, calculate_totals, get, save
from app.services.gateway_service import is_hotel_like, network_city
from app.services.vehicle_catalog_service import list_vehicle_types, list_vehicles_by_type


async def express_start(
    *,
    network: dict[str, Any],
    slug: str,
    codigo: str,
    trip_type: str,
    origin: str,
    destination: str,
    trip_date: date,
    trip_time: time,
    passenger_name: str,
    passenger_whatsapp: str,
    contributor_ref: Optional[str] = None,
    return_date: Optional[date] = None,
    return_time: Optional[time] = None,
    hourly_hours: Optional[int] = None,
) -> tuple[ExpressReservation, dict[str, Any]]:
    gateway = GatewayAPIClient()
    quote_payload = {
        "network_slug": slug,
        "network_code": codigo,
        "trip_type": trip_type,
        "origin": origin,
        "destination": destination,
        "origem": origin,
        "destino": destination,
        "trip_date": trip_date.isoformat(),
        "trip_time": trip_time.isoformat(),
        "passenger_name": passenger_name,
        "passenger_whatsapp": passenger_whatsapp,
        "contributor_ref": contributor_ref,
    }
    quote = await gateway.post_quote(slug, codigo, quote_payload)

    commission = network.get("commission_rules") or {}
    reservation = ExpressReservation.new(
        status="search",
        slug=slug,
        codigo=codigo,
        network_name=network.get("name", ""),
        network_type=network.get("type", ""),
        network_city=network_city(network),
        network_estado=str(network.get("estado") or ""),
        commission_percent=commission.get("percent"),
        trip_type=trip_type,
        origin=sanitize_text(origin, 512),
        destination=sanitize_text(
            destination if trip_type != "hourly" else (destination or f"À disposição ({hourly_hours}h)"),
            512,
        ),
        trip_date=trip_date,
        trip_time=trip_time,
        return_trip=trip_type == "round_trip",
        return_date=return_date,
        return_time=return_time,
        hourly_hours=hourly_hours,
        passenger_name=sanitize_text(passenger_name, 255),
        passenger_whatsapp=sanitize_phone(passenger_whatsapp),
        contributor_ref=contributor_ref,
        quote_id=quote.get("quote_id"),
    )
    save(reservation)
    return reservation, quote


async def express_list_vehicle_types(reservation: ExpressReservation) -> list[dict[str, Any]]:
    return await list_vehicle_types(reservation)


async def express_list_vehicles(
    reservation: ExpressReservation,
    vehicle_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    if not vehicle_type:
        return []
    return await list_vehicles_by_type(reservation, vehicle_type)


def express_select_vehicle(reservation: ExpressReservation, vehicle: dict[str, Any]) -> ExpressReservation:
    reservation.vehicle_id = str(vehicle.get("id", vehicle.get("category", "")))
    reservation.vehicle_category = normalize_vehicle_type(
        vehicle.get("vehicle_type") or vehicle.get("category")
    )
    reservation.vehicle_name = vehicle.get("name") or vehicle.get("category")
    reservation.vehicle_image_url = vehicle.get("image_url")
    calculate_totals(reservation, float(vehicle.get("price", 0)))
    reservation.status = "vehicle_selected"
    save(reservation)
    return reservation


async def express_confirm(
    reservation: ExpressReservation,
    network: dict[str, Any],
    *,
    lgpd_accepted: bool,
) -> tuple[ExpressReservation, dict[str, Any]]:
    if not lgpd_accepted:
        raise ValueError("LGPD obrigatório")

    gateway = GatewayAPIClient()
    payload = {
        "network_slug": reservation.slug,
        "network_code": reservation.codigo,
        "quote_id": reservation.quote_id,
        "trip_type": reservation.trip_type,
        "origin": reservation.origin,
        "destination": reservation.destination,
        "trip_date": reservation.trip_date.isoformat(),
        "trip_time": str(reservation.trip_time),
        "vehicle_id": reservation.vehicle_id,
        "vehicle_name": reservation.vehicle_name,
        "vehicle_category": reservation.vehicle_category,
        "total_amount": reservation.total_amount,
        "passenger_name": reservation.passenger_name,
        "passenger_whatsapp": reservation.passenger_whatsapp,
        "contributor_ref": reservation.contributor_ref,
        "lgpd_accepted": True,
    }
    result = await gateway.post_reserve(reservation.slug, reservation.codigo, payload)
    code = result.get("reservation_code") or result.get("code")
    if code:
        reservation.code = str(code)[:16]
    reservation.status = "confirmed"
    reservation.gateway_result = result
    save(reservation)
    return reservation, result


def whatsapp_url(phone: str, message: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    return f"https://wa.me/{digits}?text={quote(message)}"


def get_reservation_or_none(reservation_id: str) -> Optional[ExpressReservation]:
    return get(reservation_id)
