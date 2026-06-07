"""Modelo geografico oficial: estados/cidades via IBGE e pontos operacionais manuais."""
from datetime import datetime

from . import ibge

OPERATIONAL_POINT_TYPES = [
    "Aeroporto",
    "Hotel",
    "Centro de eventos",
    "Hub operacional",
]

OPERATIONAL_POINT_STATUSES = [
    "Operando",
    "Expansao",
    "Pendente",
    "Pausado",
]

LEGACY_OPERATIONAL_TYPES = {
    "Aeroporto",
    "Hotel",
    "Centro de eventos",
    "Regiao atendida",
}

LEGACY_STATE_TYPE = "Estado"
LEGACY_CITY_TYPE = "Cidade"


def ensure_operational_points(app):
    if not hasattr(app, "operational_points"):
        app.operational_points = []
    normalized = [normalize_operational_point(item) for item in app.operational_points]
    app.operational_points = normalized
    return normalized


def normalize_operational_point(record):
    record = dict(record or {})
    point_type = record.get("tipo", "Hub operacional")
    if point_type == "Regiao atendida":
        point_type = "Hub operacional"
    if point_type not in OPERATIONAL_POINT_TYPES:
        point_type = "Hub operacional"

    status = record.get("status", "Operando")
    if status not in OPERATIONAL_POINT_STATUSES:
        status = "Operando"

    return {
        "id": record.get("id") or next_operational_point_id([]),
        "nome": str(record.get("nome", "")).strip(),
        "tipo": point_type,
        "estado_uf": str(record.get("estado_uf") or record.get("estado", "")).upper().strip(),
        "estado_nome": str(record.get("estado_nome", "")).strip(),
        "cidade_ibge_id": int(record.get("cidade_ibge_id") or 0),
        "cidade_nome": str(record.get("cidade_nome") or record.get("cidade", "")).strip(),
        "endereco": str(record.get("endereco", "")).strip(),
        "observacoes": str(record.get("observacoes") or record.get("observacao", "")).strip(),
        "status": status,
        "legacy_coverage_id": str(record.get("legacy_coverage_id", "")).strip(),
        "criado_em": record.get("criado_em") or datetime.now().strftime("%d/%m/%Y %H:%M"),
        "atualizado_em": record.get("atualizado_em") or record.get("criado_em") or datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


def next_operational_point_id(existing):
    numbers = []
    for item in existing:
        point_id = str(item.get("id", ""))
        if point_id.startswith("op-"):
            try:
                numbers.append(int(point_id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"op-{max(numbers, default=0) + 1:04d}"


def operational_point_label(point):
    parts = [point.get("tipo", ""), point.get("nome", "")]
    location = " / ".join(part for part in [point.get("cidade_nome", ""), point.get("estado_uf", "")] if part)
    if location:
        parts.append(location)
    return " - ".join(part for part in parts if part)


def points_for_city(points, uf, cidade_ibge_id):
    uf = str(uf or "").upper()
    cidade_ibge_id = int(cidade_ibge_id or 0)
    return [
        point
        for point in points
        if point.get("estado_uf") == uf and int(point.get("cidade_ibge_id") or 0) == cidade_ibge_id
    ]


def points_for_state(points, uf):
    uf = str(uf or "").upper()
    return [point for point in points if point.get("estado_uf") == uf]


def coverage_metrics(points):
    active = sum(1 for point in points if point.get("status") == "Operando")
    states = {point.get("estado_uf") for point in points if point.get("estado_uf")}
    cities = {
        (point.get("estado_uf"), int(point.get("cidade_ibge_id") or 0))
        for point in points
        if point.get("estado_uf") and int(point.get("cidade_ibge_id") or 0)
    }
    by_type = {point_type: 0 for point_type in OPERATIONAL_POINT_TYPES}
    for point in points:
        by_type[point.get("tipo", "Hub operacional")] = by_type.get(point.get("tipo", "Hub operacional"), 0) + 1
    return {
        "total_points": len(points),
        "active_points": active,
        "states_with_points": len(states),
        "cities_with_points": len(cities),
        "by_type": by_type,
    }


def migrate_legacy_coverage(raw_state):
    """Converte registros legados de coverage para pontos operacionais e referencias geograficas."""
    legacy = list(raw_state.get("coverage") or [])
    if not legacy:
        return raw_state, False

    operational_points = [normalize_operational_point(item) for item in raw_state.get("operational_points") or []]
    existing_ids = {point.get("id") for point in operational_points}
    legacy_map = {}

    states = ibge.get_states()
    municipalities_cache = {}

    for item in legacy:
        legacy_id = str(item.get("id") or "")
        legacy_type = str(item.get("tipo", "")).strip()

        if legacy_type in LEGACY_OPERATIONAL_TYPES:
            migrated = _legacy_to_operational_point(item, states, municipalities_cache, operational_points)
            if migrated.get("id") in existing_ids:
                continue
            operational_points.append(migrated)
            existing_ids.add(migrated.get("id"))
            if legacy_id:
                legacy_map[legacy_id] = migrated.get("id")
            continue

        if legacy_type == LEGACY_STATE_TYPE:
            if legacy_id:
                legacy_map[legacy_id] = {"kind": "state", "uf": _resolve_state_uf(item, states)}
            continue

        if legacy_type == LEGACY_CITY_TYPE:
            city_ref = _resolve_city_ref(item, states, municipalities_cache)
            if legacy_id:
                legacy_map[legacy_id] = {"kind": "city", **city_ref}
            continue

    drivers = [_migrate_driver_coverage(driver, legacy_map) for driver in raw_state.get("drivers") or []]
    clients = [_migrate_client_coverage(client, legacy_map) for client in raw_state.get("clients") or []]

    migrated_state = dict(raw_state)
    migrated_state["operational_points"] = operational_points
    migrated_state["drivers"] = drivers
    migrated_state["clients"] = clients
    migrated_state["coverage"] = []
    migrated_state["_geo_migrated"] = True
    migrated_state["_geo_migrated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    return migrated_state, True


def _legacy_to_operational_point(item, states, municipalities_cache, existing_points):
    uf = _resolve_state_uf(item, states)
    city_name = str(item.get("cidade", "")).strip()
    city_ref = {"cidade_ibge_id": 0, "cidade_nome": city_name}
    if uf and city_name:
        if uf not in municipalities_cache:
            municipalities_cache[uf] = ibge.get_municipalities(uf)
        match = ibge.find_municipality_by_name(municipalities_cache[uf], city_name)
        if match:
            city_ref = {"cidade_ibge_id": match["id"], "cidade_nome": match["nome"]}

    state = ibge.find_state_by_sigla(states, uf)
    legacy_id = str(item.get("id") or "")
    point_id = legacy_id if legacy_id.startswith("op-") else next_operational_point_id(existing_points)

    return normalize_operational_point(
        {
            "id": point_id,
            "nome": item.get("nome", ""),
            "tipo": "Hub operacional" if item.get("tipo") == "Regiao atendida" else item.get("tipo"),
            "estado_uf": uf,
            "estado_nome": state.get("nome", "") if state else str(item.get("estado", "")),
            "endereco": item.get("endereco", ""),
            "observacoes": item.get("observacoes") or item.get("observacao", "") or item.get("demanda", ""),
            "status": item.get("status", "Operando"),
            "legacy_coverage_id": legacy_id,
            **city_ref,
        }
    )


def _resolve_state_uf(item, states):
    uf = str(item.get("estado_uf") or item.get("estado") or item.get("sigla") or "").upper().strip()
    if len(uf) == 2:
        return uf
    name = str(item.get("nome", "")).strip()
    for state in states:
        if state.get("nome", "").lower() == name.lower() or state.get("sigla", "").lower() == name.lower():
            return state.get("sigla", "")
    return uf[:2] if uf else ""


def _resolve_city_ref(item, states, municipalities_cache):
    uf = _resolve_state_uf(item, states)
    city_name = str(item.get("cidade") or item.get("nome") or "").strip()
    if not uf or not city_name:
        return {"estado_uf": uf, "cidade_ibge_id": 0, "cidade_nome": city_name}
    if uf not in municipalities_cache:
        municipalities_cache[uf] = ibge.get_municipalities(uf)
    match = ibge.find_municipality_by_name(municipalities_cache[uf], city_name)
    if match:
        return {"estado_uf": uf, "cidade_ibge_id": match["id"], "cidade_nome": match["nome"]}
    return {"estado_uf": uf, "cidade_ibge_id": 0, "cidade_nome": city_name}


def _migrate_driver_coverage(driver, legacy_map):
    driver = dict(driver or {})
    operational_point_ids = list(driver.get("operational_point_ids") or driver.get("coverage_ids") or [])
    estados_uf = list(driver.get("estados_uf") or [])
    cidades = list(driver.get("cidades_ibge") or [])

    resolved_points = []
    for legacy_id in operational_point_ids:
        mapped = legacy_map.get(str(legacy_id))
        if isinstance(mapped, str):
            resolved_points.append(mapped)
        elif isinstance(mapped, dict):
            if mapped.get("kind") == "state" and mapped.get("uf") and mapped["uf"] not in estados_uf:
                estados_uf.append(mapped["uf"])
            if mapped.get("kind") == "city" and mapped.get("cidade_ibge_id"):
                cidades.append(
                    {
                        "estado_uf": mapped.get("estado_uf", ""),
                        "ibge_id": mapped.get("cidade_ibge_id", 0),
                        "nome": mapped.get("cidade_nome", ""),
                    }
                )
        elif str(legacy_id).startswith("op-"):
            resolved_points.append(str(legacy_id))

    driver["operational_point_ids"] = list(dict.fromkeys(resolved_points))
    driver["estados_uf"] = list(dict.fromkeys(estados_uf))
    driver["cidades_ibge"] = _dedupe_cities(cidades)
    driver.pop("coverage_ids", None)
    return driver


def _migrate_client_coverage(client, legacy_map):
    client = dict(client or {})
    if not client.get("operational_point_ids") and not client.get("coverage_ids"):
        return client
    operational_point_ids = list(client.get("operational_point_ids") or client.get("coverage_ids") or [])
    resolved = []
    estados_uf = list(client.get("estados_uf") or [])
    cidades = list(client.get("cidades_ibge") or [])
    for legacy_id in operational_point_ids:
        mapped = legacy_map.get(str(legacy_id))
        if isinstance(mapped, str):
            resolved.append(mapped)
        elif isinstance(mapped, dict):
            if mapped.get("kind") == "state" and mapped.get("uf") and mapped["uf"] not in estados_uf:
                estados_uf.append(mapped["uf"])
            if mapped.get("kind") == "city" and mapped.get("cidade_ibge_id"):
                cidades.append(
                    {
                        "estado_uf": mapped.get("estado_uf", ""),
                        "ibge_id": mapped.get("cidade_ibge_id", 0),
                        "nome": mapped.get("cidade_nome", ""),
                    }
                )
        elif str(legacy_id).startswith("op-"):
            resolved.append(str(legacy_id))
    client["operational_point_ids"] = list(dict.fromkeys(resolved))
    client["estados_uf"] = list(dict.fromkeys(estados_uf))
    client["cidades_ibge"] = _dedupe_cities(cidades)
    client.pop("coverage_ids", None)
    return client


def _dedupe_cities(cities):
    seen = set()
    unique = []
    for city in cities:
        key = (city.get("estado_uf", ""), int(city.get("ibge_id") or city.get("cidade_ibge_id") or 0))
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "estado_uf": city.get("estado_uf", ""),
                "ibge_id": int(city.get("ibge_id") or city.get("cidade_ibge_id") or 0),
                "nome": city.get("nome") or city.get("cidade_nome", ""),
            }
        )
    return unique
