"""CRUD de abrangencia (pontos operacionais) — logica extraida de coverage_ui.py (sem Tkinter)."""
from __future__ import annotations

from datetime import datetime

from app import ibge
from app.geography import (
    OPERATIONAL_POINT_STATUSES,
    OPERATIONAL_POINT_TYPES,
    coverage_metrics,
    ensure_operational_points,
    next_operational_point_id,
    normalize_operational_point,
    operational_point_label,
    points_for_state,
)
from app.operational_network import enrich_operational_point

PO_RESERVATION_KEYS = (
    "embarque_po_id",
    "desembarque_po_id",
    "volta_embarque_po_id",
    "volta_desembarque_po_id",
)
BLOCKED_STATUSES = {"pausado"}
ACTIVE_STATUS = "Operando"


def point_display_name(point):
    return operational_point_label(point)


def list_states(*, force_refresh=False):
    return ibge.get_states(force_refresh=force_refresh)


def list_municipalities(uf, *, force_refresh=False):
    return ibge.get_municipalities(uf, force_refresh=force_refresh)


def list_coverage_points(
    app,
    *,
    search="",
    tipo="",
    status="",
    uf="",
    include_blocked=True,
):
    ensure_operational_points(app)
    items = []
    query = str(search or "").strip().lower()
    tipo_filter = str(tipo or "").strip()
    status_filter = str(status or "").strip()
    uf_filter = str(uf or "").strip().upper()

    for point in getattr(app, "operational_points", []) or []:
        point_status = str(point.get("status", "")).strip()
        if not include_blocked and point_status.lower() in BLOCKED_STATUSES:
            continue
        if tipo_filter and point.get("tipo") != tipo_filter:
            continue
        if status_filter and point_status != status_filter:
            continue
        if uf_filter and str(point.get("estado_uf", "")).upper() != uf_filter:
            continue
        if query:
            haystack = " ".join(
                [
                    point.get("nome", ""),
                    point.get("tipo", ""),
                    point.get("endereco", ""),
                    point.get("cidade_nome", ""),
                    point.get("estado_uf", ""),
                    point.get("id", ""),
                ]
            ).lower()
            if query not in haystack:
                continue
        items.append(point)

    items.sort(key=lambda row: point_display_name(row).lower())
    return items


def find_point_by_id(app, point_id):
    point_id = str(point_id or "")
    for point in getattr(app, "operational_points", []) or []:
        if str(point.get("id", "")) == point_id:
            return point
    return None


def _resolve_geo_names(uf, cidade_ibge_id, cidade_nome=""):
    states = list_states()
    state = ibge.find_state_by_sigla(states, uf)
    estado_nome = state.get("nome", "") if state else ""
    cidade_nome = str(cidade_nome or "").strip()
    cidade_ibge_id = int(cidade_ibge_id or 0)
    if uf and cidade_ibge_id and not cidade_nome:
        for city in list_municipalities(uf):
            if int(city.get("id") or 0) == cidade_ibge_id:
                cidade_nome = city.get("nome", "")
                break
    return estado_nome, cidade_nome


def _build_point_payload(form_data, *, existing=None):
    existing = existing or {}
    uf = str(form_data.get("estado_uf") or existing.get("estado_uf") or "").upper().strip()
    try:
        cidade_ibge_id = int(form_data.get("cidade_ibge_id") or existing.get("cidade_ibge_id") or 0)
    except (TypeError, ValueError):
        cidade_ibge_id = int(existing.get("cidade_ibge_id") or 0)
    cidade_nome = str(form_data.get("cidade_nome") or existing.get("cidade_nome") or "").strip()
    estado_nome, cidade_nome = _resolve_geo_names(uf, cidade_ibge_id, cidade_nome)

    raw = {
        "id": existing.get("id"),
        "nome": str(form_data.get("nome", existing.get("nome", ""))).strip(),
        "tipo": str(form_data.get("tipo", existing.get("tipo", OPERATIONAL_POINT_TYPES[0]))).strip(),
        "estado_uf": uf,
        "estado_nome": estado_nome or existing.get("estado_nome", ""),
        "cidade_ibge_id": cidade_ibge_id,
        "cidade_nome": cidade_nome,
        "endereco": str(form_data.get("endereco", existing.get("endereco", ""))).strip(),
        "observacoes": str(form_data.get("observacoes", existing.get("observacoes", ""))).strip(),
        "status": str(form_data.get("status", existing.get("status", ACTIVE_STATUS))).strip(),
        "legacy_coverage_id": existing.get("legacy_coverage_id", ""),
        "criado_em": existing.get("criado_em") or datetime.now().strftime("%d/%m/%Y %H:%M"),
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "portal_publicado": existing.get("portal_publicado", True),
        "website_slug": existing.get("website_slug", ""),
        "website_path": existing.get("website_path", ""),
        "contato": str(form_data.get("contato", existing.get("contato", ""))).strip(),
    }
    portal = form_data.get("portal_publicado")
    if portal is not None:
        raw["portal_publicado"] = portal in {"1", "true", "on", True, "Sim", "sim"}
    return enrich_operational_point(normalize_operational_point(raw))


def create_coverage_point(app, form_data):
    ensure_operational_points(app)
    points = getattr(app, "operational_points", []) or []
    payload = _build_point_payload(form_data)
    payload["id"] = next_operational_point_id(points)
    points.insert(0, payload)
    app.operational_points = points
    if hasattr(app, "save_state"):
        app.save_state()
    return payload


def update_coverage_point(app, point_id, form_data):
    point = find_point_by_id(app, point_id)
    if not point:
        raise ValueError("ponto_nao_encontrado")
    payload = _build_point_payload(form_data, existing=point)
    point.update(payload)
    if hasattr(app, "save_state"):
        app.save_state()
    return point


def block_coverage_point(app, point_id):
    point = find_point_by_id(app, point_id)
    if not point:
        raise ValueError("ponto_nao_encontrado")
    point["status"] = "Pausado"
    point["portal_publicado"] = False
    point["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    if hasattr(app, "save_state"):
        app.save_state()
    return point


def activate_coverage_point(app, point_id):
    point = find_point_by_id(app, point_id)
    if not point:
        raise ValueError("ponto_nao_encontrado")
    point["status"] = ACTIVE_STATUS
    point["portal_publicado"] = True
    point["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    enriched = enrich_operational_point(point)
    point.update(enriched)
    if hasattr(app, "save_state"):
        app.save_state()
    return point


def linked_drivers(app, point):
    pid = str(point.get("id", ""))
    uf = str(point.get("estado_uf", "")).upper()
    cidade_id = int(point.get("cidade_ibge_id") or 0)
    items = []
    seen = set()
    for driver in getattr(app, "drivers", []) or []:
        did = str(driver.get("id", ""))
        if did in seen:
            continue
        op_ids = [str(x) for x in (driver.get("operational_point_ids") or [])]
        if pid and pid in op_ids:
            items.append(driver)
            seen.add(did)
            continue
        estados = [str(x).upper() for x in (driver.get("estados_uf") or [])]
        if uf and uf in estados and not op_ids:
            items.append(driver)
            seen.add(did)
            continue
        for city in driver.get("cidades_ibge") or []:
            if (
                str(city.get("estado_uf", "")).upper() == uf
                and int(city.get("ibge_id") or city.get("cidade_ibge_id") or 0) == cidade_id
                and cidade_id > 0
            ):
                items.append(driver)
                seen.add(did)
                break
    return items


def linked_reservations(app, point):
    pid = str(point.get("id", ""))
    items = []
    for reservation in getattr(app, "reservations", []) or []:
        for key in PO_RESERVATION_KEYS:
            if str(reservation.get(key, "")) == pid:
                items.append(reservation)
                break
    return items


def linked_vehicles(app, point):
    drivers = linked_drivers(app, point)
    driver_ids = {str(d.get("id", "")) for d in drivers}
    reservations = linked_reservations(app, point)
    items = []
    seen = set()
    for vehicle in getattr(app, "vehicles", []) or []:
        vid = str(vehicle.get("id", ""))
        if vid in seen:
            continue
        if str(vehicle.get("driver_id", "")) in driver_ids:
            items.append(vehicle)
            seen.add(vid)
    for reservation in reservations:
        vid = str(reservation.get("vehicle_id", ""))
        if not vid or vid in seen:
            continue
        for vehicle in getattr(app, "vehicles", []) or []:
            if str(vehicle.get("id", "")) == vid:
                items.append(vehicle)
                seen.add(vid)
                break
    return items


def point_stats(app, point):
    reservations = linked_reservations(app, point)
    drivers = linked_drivers(app, point)
    vehicles = linked_vehicles(app, point)
    return {
        "total_reservas": len(reservations),
        "motoristas_vinculados": len(drivers),
        "veiculos_vinculados": len(vehicles),
        "status": point.get("status", ""),
        "portal_publicado": bool(point.get("portal_publicado", True)),
        "tipo": point.get("tipo", ""),
    }


def list_summary(app):
    ensure_operational_points(app)
    points = getattr(app, "operational_points", []) or []
    metrics = coverage_metrics(points)
    states_ibge = len(list_states())
    return {
        "total": metrics["total_points"],
        "ativos": metrics["active_points"],
        "estados_ibge": states_ibge,
        "estados_com_pontos": metrics["states_with_points"],
        "cidades_com_pontos": metrics["cities_with_points"],
        "por_tipo": metrics["by_type"],
    }


def filter_options():
    return {
        "tipos": OPERATIONAL_POINT_TYPES,
        "statuses": OPERATIONAL_POINT_STATUSES,
        "ufs": [state.get("sigla", "") for state in list_states()],
    }
