"""Catálogo de tipos e veículos por cidade da rede — Supabase Master + Gateway."""

from __future__ import annotations

from typing import Any, Optional

from app.clients.gateway_api import GatewayAPIClient, normalize_vehicle
from app.clients.supabase_client import SupabaseClient
from app.domain.vehicle_types import VEHICLE_TYPES, normalize_vehicle_type, type_icon
from app.services.express_store import ExpressReservation
from app.services.gateway_service import fetch_network, network_city


def _normalize_catalog_item(raw: dict[str, Any]) -> dict[str, Any]:
    item = normalize_vehicle(raw)
    vehicle_type = normalize_vehicle_type(item.get("category") or item.get("tipo_veiculo"))
    item["vehicle_type"] = vehicle_type
    item["category"] = vehicle_type
    if not item.get("name"):
        brand = str(item.get("brand") or item.get("marca") or "").strip()
        model = str(item.get("model") or item.get("modelo") or "").strip()
        plate = str(item.get("plate") or item.get("placa") or "").strip()
        base = f"{brand} {model}".strip() or vehicle_type
        item["name"] = f"{base} · {plate}" if plate else base
    return item


async def _resolve_city(reservation: ExpressReservation) -> str:
    if getattr(reservation, "network_city", None):
        return reservation.network_city
    network = await fetch_network(reservation.slug, reservation.codigo)
    return network_city(network)


async def _load_city_vehicles(city: str, slug: str, codigo: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    supabase = SupabaseClient()
    if supabase.enabled and city:
        raw = await supabase.rpc("motor_list_vehicles_by_city", {"p_cidade": city, "p_tipo": None})
        if isinstance(raw, list):
            items = [_normalize_catalog_item(v) for v in raw if isinstance(v, dict)]

    if not items:
        gateway = GatewayAPIClient()
        gateway_items = await gateway.get_vehicles(slug, codigo)
        for raw in gateway_items:
            if isinstance(raw, dict):
                mapped = {
                    "id": raw.get("id") or raw.get("id_admin"),
                    "category": raw.get("categoria") or raw.get("category"),
                    "name": f'{raw.get("marca", "")} {raw.get("modelo", "")}'.strip(),
                    "brand": raw.get("marca"),
                    "model": raw.get("modelo"),
                    "image_url": raw.get("foto") or raw.get("image_url"),
                    "passengers": raw.get("capacidade") or raw.get("passengers") or 3,
                    "luggage": raw.get("bagagens") or raw.get("luggage") or 3,
                    "price": raw.get("price") or raw.get("preco_base") or 0,
                    "cidade": raw.get("cidade") or city,
                }
                items.append(_normalize_catalog_item(mapped))

    return items


async def _quote_price(
    reservation: ExpressReservation,
    vehicle_type: str,
    vehicle: dict[str, Any],
) -> float:
    price = float(vehicle.get("price") or 0)
    if price > 0:
        return price
    gateway = GatewayAPIClient()
    quote = await gateway.post_quote(
        reservation.slug,
        reservation.codigo,
        {
            "network_slug": reservation.slug,
            "network_code": reservation.codigo,
            "trip_type": reservation.trip_type,
            "origin": reservation.origin,
            "destination": reservation.destination,
            "origem": reservation.origin,
            "destino": reservation.destination,
            "trip_date": reservation.trip_date.isoformat(),
            "trip_time": str(reservation.trip_time),
            "categoria": vehicle_type,
            "quote_id": reservation.quote_id,
        },
    )
    options = (quote.get("quote") or {}).get("options") or quote.get("options") or []
    if options:
        return float(options[0].get("valor_estimado") or options[0].get("price") or 0)
    return float(quote.get("valor_estimado") or quote.get("price") or 0)


async def list_vehicle_types(reservation: ExpressReservation) -> list[dict[str, Any]]:
    city = await _resolve_city(reservation)
    vehicles = await _load_city_vehicles(city, reservation.slug, reservation.codigo)
    grouped: dict[str, dict[str, Any]] = {}
    for vehicle in vehicles:
        vtype = vehicle["vehicle_type"]
        bucket = grouped.setdefault(
            vtype,
            {
                "type": vtype,
                "label": vtype,
                "count": 0,
                "min_price": None,
                "image_url": type_icon(vtype),
                "cidade": city,
            },
        )
        bucket["count"] += 1
        price = float(vehicle.get("price") or 0)
        if price > 0 and (bucket["min_price"] is None or price < bucket["min_price"]):
            bucket["min_price"] = price

    ordered = [grouped[t] for t in VEHICLE_TYPES if t in grouped]
    for t, data in grouped.items():
        if t not in VEHICLE_TYPES:
            ordered.append(data)
    return ordered


async def list_vehicles_by_type(
    reservation: ExpressReservation,
    vehicle_type: str,
) -> list[dict[str, Any]]:
    city = await _resolve_city(reservation)
    normalized = normalize_vehicle_type(vehicle_type)
    vehicles = await _load_city_vehicles(city, reservation.slug, reservation.codigo)
    filtered = [v for v in vehicles if v.get("vehicle_type") == normalized]
    result: list[dict[str, Any]] = []
    for vehicle in filtered:
        item = dict(vehicle)
        item["price"] = await _quote_price(reservation, normalized, item)
        result.append(item)
    result.sort(key=lambda v: (v.get("price") or 0, v.get("name") or ""))
    return result
