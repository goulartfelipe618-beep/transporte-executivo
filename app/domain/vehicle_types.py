"""Tipos de veículo alinhados ao Sistema Master (vehicles_model.VEHICLE_TYPES)."""

from __future__ import annotations

from typing import Any

VEHICLE_TYPES: tuple[str, ...] = (
    "CARRO EXECUTIVO",
    "CARRO POPULAR",
    "TAXI",
    "VAN",
    "MICRO-ONIBUS",
)

_LEGACY_TYPE_MAP: dict[str, str] = {
    "carro": "CARRO EXECUTIVO",
    "suv": "CARRO EXECUTIVO",
    "executivo": "CARRO EXECUTIVO",
    "sedan executivo": "CARRO EXECUTIVO",
    "suv executivo": "CARRO EXECUTIVO",
    "sedan": "CARRO EXECUTIVO",
    "popular": "CARRO POPULAR",
    "carro popular": "CARRO POPULAR",
    "taxi": "TAXI",
    "van": "VAN",
    "van executiva": "VAN",
    "micro-onibus": "MICRO-ONIBUS",
    "micro-ônibus": "MICRO-ONIBUS",
    "onibus": "MICRO-ONIBUS",
    "ônibus": "MICRO-ONIBUS",
}

TYPE_ICONS: dict[str, str] = {
    "CARRO EXECUTIVO": "/static/images/vehicles/sedan.svg",
    "CARRO POPULAR": "/static/images/vehicles/sedan.svg",
    "TAXI": "/static/images/vehicles/sedan.svg",
    "VAN": "/static/images/vehicles/van.svg",
    "MICRO-ONIBUS": "/static/images/vehicles/van.svg",
}


def normalize_vehicle_type(tipo: Any) -> str:
    raw = str(tipo or "").strip()
    if raw in VEHICLE_TYPES:
        return raw
    mapped = _LEGACY_TYPE_MAP.get(raw.lower())
    if mapped:
        return mapped
    upper = raw.upper()
    if upper in VEHICLE_TYPES:
        return upper
    for master_type in VEHICLE_TYPES:
        if master_type.lower() in raw.lower() or raw.lower() in master_type.lower():
            return master_type
    return VEHICLE_TYPES[0]


def type_icon(vehicle_type: str) -> str:
    return TYPE_ICONS.get(vehicle_type, "/static/images/vehicles/sedan.svg")
