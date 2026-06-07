"""DTOs publicos — Gateway V1. Nunca serializar entidades internas diretamente."""
from __future__ import annotations

from .operational_network import active_network_points, ensure_operational_network
from .platform_contract import CONTRACT_VERSION, build_coverage_summary

SEGMENT_TYPE_MAP = {
    "airports": {"Aeroporto"},
    "aeroportos": {"Aeroporto"},
    "hotels": {"Hotel"},
    "hoteis": {"Hotel"},
    "events": {"Centro de eventos", "Centro de convencoes"},
    "eventos": {"Centro de eventos", "Centro de convencoes"},
    "partners": {"Parceiro corporativo"},
    "hubs": {"Hub operacional"},
    "support-points": {"Ponto de apoio"},
}

TYPE_ALIASES = {
    "aeroporto": "Aeroporto",
    "hotel": "Hotel",
    "centro-de-eventos": "Centro de eventos",
    "centro-de-convencoes": "Centro de convencoes",
    "hub": "Hub operacional",
    "parceiro": "Parceiro corporativo",
    "ponto-de-apoio": "Ponto de apoio",
}


def _published_points(app):
    ensure_operational_network(app)
    return active_network_points(app, public_only=True)


def _corporate_count(app):
    clients = list(getattr(app, "clients", []))
    corporate = [c for c in clients if c.get("tipo_pessoa") == "juridica" or c.get("cnpj")]
    active = [
        c
        for c in corporate
        if str(c.get("status_empresa", c.get("status", "Ativa"))).lower() not in {"inativa", "bloqueada"}
    ]
    return len(active) or len(corporate)


def _homologated_drivers(app):
    drivers = list(getattr(app, "drivers", []))
    homologated = [
        d
        for d in drivers
        if str(d.get("status_operacional", d.get("frota", ""))).lower() in {"ativo", "homologado", "operando"}
    ]
    return len(homologated) or len(drivers)


def build_public_stats(app) -> dict:
    """GET /api/v1/public/stats — totais agregados para o Website."""
    points = _published_points(app)
    states = {p.get("estado_uf") for p in points if p.get("estado_uf")}
    cities = {(p.get("estado_uf"), p.get("cidade_nome")) for p in points if p.get("cidade_nome")}
    vehicles = build_public_vehicles(app)
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "companies": _corporate_count(app),
        "drivers": _homologated_drivers(app),
        "vehicles": len(vehicles),
        "operational_points": len(points),
        "states": len(states),
        "cities": len(cities),
    }


def build_public_coverage(app) -> dict:
    """GET /api/v1/public/coverage — estados e cidades atendidos."""
    points = _published_points(app)
    state_map = {}
    city_map = {}
    for point in points:
        uf = point.get("estado_uf", "")
        city = point.get("cidade_nome", "")
        if uf:
            entry = state_map.setdefault(uf, {"uf": uf, "operational_points": 0})
            entry["operational_points"] += 1
        if uf and city:
            key = (uf, city)
            entry = city_map.setdefault(key, {"uf": uf, "cidade": city, "operational_points": 0})
            entry["operational_points"] += 1
    states = sorted(state_map.values(), key=lambda item: item["uf"])
    cities = sorted(city_map.values(), key=lambda item: (item["uf"], item["cidade"]))
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "states": states,
        "cities": cities,
        "totals": {
            "states": len(states),
            "cities": len(cities),
            "operational_points": len(points),
        },
    }


def _normalize_type_filter(raw):
    value = str(raw or "").strip()
    if not value:
        return None
    lower = value.lower()
    if lower in SEGMENT_TYPE_MAP:
        return SEGMENT_TYPE_MAP[lower]
    if lower in TYPE_ALIASES:
        return {TYPE_ALIASES[lower]}
    return {value}


def build_public_location_dto(point: dict) -> dict:
    point = dict(point or {})
    return {
        "id": point.get("id", ""),
        "nome": point.get("nome", ""),
        "tipo": point.get("tipo", ""),
        "cidade": point.get("cidade_nome", ""),
        "estado": point.get("estado_uf", ""),
        "endereco": point.get("endereco", ""),
        "website_slug": point.get("website_slug", ""),
        "website_path": point.get("website_path", ""),
    }


def build_public_location_detail(point: dict) -> dict:
    dto = build_public_location_dto(point)
    return {
        "nome": dto["nome"],
        "tipo": dto["tipo"],
        "cidade": dto["cidade"],
        "estado": dto["estado"],
        "website_slug": dto["website_slug"],
        "website_path": dto["website_path"],
    }


def build_public_locations(app, *, type_filter=None, state_filter=None, city_filter=None) -> list:
    points = _published_points(app)
    allowed_types = _normalize_type_filter(type_filter)
    state_filter = str(state_filter or "").strip().upper() or None
    city_filter = str(city_filter or "").strip().lower() or None

    items = []
    for point in points:
        if allowed_types and point.get("tipo") not in allowed_types:
            continue
        if state_filter and str(point.get("estado_uf", "")).upper() != state_filter:
            continue
        if city_filter and city_filter not in str(point.get("cidade_nome", "")).lower():
            continue
        items.append(build_public_location_dto(point))
    return items


def build_public_vehicles(app) -> list:
    items = []
    for vehicle in getattr(app, "vehicles", []):
        if str(vehicle.get("status", "Ativo")).lower() not in {"ativo", "operando"}:
            continue
        if str(vehicle.get("portal_publicado", True)).lower() in {"nao", "false", "0"}:
            continue
        imagem = vehicle.get("capa") or vehicle.get("foto") or vehicle.get("imagem") or ""
        items.append(
            {
                "id": vehicle.get("id") or vehicle.get("placa", ""),
                "categoria": vehicle.get("tipo_veiculo") or vehicle.get("categoria", ""),
                "capacidade": vehicle.get("capacidade", vehicle.get("passageiros", "")),
                "aplicacao": vehicle.get("aplicacao", vehicle.get("tipo_veiculo", "")),
                "marca": vehicle.get("marca", ""),
                "modelo": vehicle.get("modelo", ""),
                "imagem": imagem,
            }
        )
    return items


def build_public_segment(app, segment: str) -> list:
    allowed = SEGMENT_TYPE_MAP.get(str(segment or "").lower(), set())
    if not allowed:
        return []
    return build_public_locations(app, type_filter=next(iter(allowed)) if len(allowed) == 1 else None)


def build_public_airports(app) -> list:
    return [item for item in build_public_locations(app) if item.get("tipo") == "Aeroporto"]


def build_public_hotels(app) -> list:
    return [item for item in build_public_locations(app) if item.get("tipo") == "Hotel"]


def build_public_events(app) -> list:
    allowed = SEGMENT_TYPE_MAP["events"]
    return [item for item in build_public_locations(app) if item.get("tipo") in allowed]


def find_public_location_by_slug(app, slug: str):
    slug = str(slug or "").strip().lower()
    for point in _published_points(app):
        if str(point.get("website_slug", "")).lower() == slug:
            return build_public_location_detail(point)
    return None


def build_public_statistics_legacy(app) -> dict:
    """Compatibilidade PLATFORM_CONTRACT — /api/v1/public/statistics."""
    return {"ok": True, **build_coverage_summary(app)}
