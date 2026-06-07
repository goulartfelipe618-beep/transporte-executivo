"""Tipos de veiculo e regras de veiculo de rede vs reserva manual."""
from __future__ import annotations

VEHICLE_TYPES = (
    "CARRO EXECUTIVO",
    "CARRO POPULAR",
    "TAXI",
    "VAN",
    "MICRO-ONIBUS",
)

VEHICLE_OPERATIONAL_FIELDS = (
    "valor_km",
    "valor_hora",
    "tarifa_base",
    "valor_minimo",
    "distancia_minima",
    "tipo_cobranca",
    "tolerancia_min",
    "valor_hora_espera",
    "fracao_min",
    "multiplicador_ida_volta",
    "preco_fixo_rota",
    "taxa_noturna",
    "taxa_aeroporto",
    "pedagio",
    "taxas_extras",
)

_LEGACY_TYPE_MAP = {
    "carro": "CARRO EXECUTIVO",
    "suv": "CARRO EXECUTIVO",
    "executivo": "CARRO EXECUTIVO",
    "popular": "CARRO POPULAR",
    "taxi": "TAXI",
    "van": "VAN",
    "micro-onibus": "MICRO-ONIBUS",
    "micro-ônibus": "MICRO-ONIBUS",
    "onibus": "MICRO-ONIBUS",
    "ônibus": "MICRO-ONIBUS",
}


def _parse_money(value):
    raw = str(value or "").replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.0


def normalize_vehicle_type(tipo):
    raw = str(tipo or "").strip()
    if raw in VEHICLE_TYPES:
        return raw
    return _LEGACY_TYPE_MAP.get(raw.lower(), VEHICLE_TYPES[0])


def is_network_vehicle(vehicle):
    if not vehicle:
        return False
    raw = vehicle.get("veiculo_de_rede")
    if raw is not None and str(raw).strip() != "":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"sim", "true", "1", "yes"}
    if _parse_money(vehicle.get("valor_km")) > 0:
        return True
    published = str(vehicle.get("portal_publicado", "")).lower()
    return published in {"sim", "true", "1", "yes"}


def clear_operational_fields(values):
    for key in VEHICLE_OPERATIONAL_FIELDS:
        values[key] = ""


def apply_network_flags(values, network_vehicle):
    values["veiculo_de_rede"] = "Sim" if network_vehicle else "Nao"
    values["portal_publicado"] = network_vehicle
    if not network_vehicle:
        clear_operational_fields(values)
