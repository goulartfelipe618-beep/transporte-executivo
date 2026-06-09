"""CRUD de veiculos — logica extraida de pages.py (sem Tkinter)."""
from __future__ import annotations

from app.portal_auth import find_driver_by_id
from app.repository.ids import next_entity_id
from app.vehicles_model import (
    VEHICLE_TYPES,
    apply_network_flags,
    is_network_vehicle,
    normalize_vehicle_type,
)

from ..validators.vehicle import DOCUMENT_FIELDS, IMAGE_FIELDS

DONE_STATUSES = {"concluida", "concluído", "concluido", "finalizada"}
CANCEL_STATUSES = {"cancelada", "cancelado", "rejeitada"}


def vehicle_display_name(vehicle):
    marca = str(vehicle.get("marca", "")).strip()
    modelo = str(vehicle.get("modelo", "")).strip()
    placa = str(vehicle.get("placa", "")).strip()
    base = f"{marca} {modelo}".strip()
    return f"{base} ({placa})" if placa else (base or vehicle.get("id", ""))


def list_vehicles(app, *, search="", include_inactive=True):
    items = []
    query = str(search or "").strip().lower()
    for vehicle in getattr(app, "vehicles", []) or []:
        status = str(vehicle.get("status", "Ativo"))
        if not include_inactive and status.lower() in {"inativo", "manutencao"}:
            continue
        if query:
            haystack = " ".join(
                [
                    vehicle.get("marca", ""),
                    vehicle.get("modelo", ""),
                    vehicle.get("placa", ""),
                    vehicle.get("tipo_veiculo", ""),
                    vehicle.get("id", ""),
                ]
            ).lower()
            if query not in haystack:
                continue
        items.append(vehicle)
    items.sort(key=lambda row: vehicle_display_name(row).lower())
    return items


def find_vehicle_by_id(app, vehicle_id):
    vehicle_id = str(vehicle_id or "")
    for vehicle in getattr(app, "vehicles", []) or []:
        if str(vehicle.get("id", "")) == vehicle_id:
            return vehicle
    return None


def _build_vehicle_payload(form_data, *, existing=None):
    existing = existing or {}
    payload = dict(existing)
    scalar_fields = [
        "tipo_veiculo",
        "status",
        "marca",
        "modelo",
        "ano",
        "cor",
        "placa",
        "combustivel",
        "renavam",
        "chassi",
        "capacidade",
        "bagagens",
        "aplicacao",
        "driver_id",
        "observacoes",
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
    ]
    for key in scalar_fields:
        if key in form_data:
            payload[key] = str(form_data.get(key, "")).strip()
    for key in IMAGE_FIELDS:
        if key in form_data:
            payload[key] = str(form_data.get(key, "")).strip()
    network = form_data.get("veiculo_de_rede")
    if network is not None:
        payload["veiculo_de_rede"] = "Sim" if network in {"1", "true", "on", True, "Sim", "sim"} else "Nao"
    payload["tipo_veiculo"] = normalize_vehicle_type(payload.get("tipo_veiculo"))
    network_vehicle = payload.get("veiculo_de_rede") == "Sim"
    apply_network_flags(payload, network_vehicle)
    return payload


def create_vehicle(app, form_data):
    vehicles = getattr(app, "vehicles", []) or []
    payload = _build_vehicle_payload(form_data)
    payload["id"] = next_entity_id("veh", vehicles)
    vehicles.insert(0, payload)
    app.vehicles = vehicles
    if hasattr(app, "save_state"):
        app.save_state()
    return payload


def update_vehicle(app, vehicle_id, form_data):
    vehicle = find_vehicle_by_id(app, vehicle_id)
    if not vehicle:
        raise ValueError("veiculo_nao_encontrado")
    payload = _build_vehicle_payload(form_data, existing=vehicle)
    vehicle.update(payload)
    if hasattr(app, "save_state"):
        app.save_state()
    return vehicle


def block_vehicle(app, vehicle_id):
    vehicle = find_vehicle_by_id(app, vehicle_id)
    if not vehicle:
        raise ValueError("veiculo_nao_encontrado")
    vehicle["status"] = "Inativo"
    vehicle["portal_publicado"] = False
    if hasattr(app, "save_state"):
        app.save_state()
    return vehicle


def activate_vehicle(app, vehicle_id):
    vehicle = find_vehicle_by_id(app, vehicle_id)
    if not vehicle:
        raise ValueError("veiculo_nao_encontrado")
    vehicle["status"] = "Ativo"
    if is_network_vehicle(vehicle):
        vehicle["portal_publicado"] = True
    if hasattr(app, "save_state"):
        app.save_state()
    return vehicle


def list_vehicle_images(vehicle):
    rows = []
    for key in IMAGE_FIELDS:
        value = str(vehicle.get(key, "")).strip()
        if value:
            rows.append({"key": key, "label": key.replace("img_", "").replace("_", " ").title(), "path": value})
    return rows


def list_vehicle_documents(vehicle):
    rows = []
    for key in DOCUMENT_FIELDS:
        value = str(vehicle.get(key, "")).strip()
        if value:
            rows.append({"key": key, "label": key.upper(), "value": value})
    if vehicle.get("renavam") or vehicle.get("chassi"):
        pass
    extra_docs = [
        ("ano", "Ano"),
        ("cor", "Cor"),
        ("combustivel", "Combustivel"),
    ]
    for key, label in extra_docs:
        value = str(vehicle.get(key, "")).strip()
        if value and key not in {r["key"] for r in rows}:
            rows.append({"key": key, "label": label, "value": value})
    return rows


def linked_drivers(app, vehicle):
    driver_id = str(vehicle.get("driver_id", "")).strip()
    tipo = normalize_vehicle_type(vehicle.get("tipo_veiculo", "")).lower()
    items = []
    seen = set()
    if driver_id:
        driver = find_driver_by_id(app, driver_id)
        if driver:
            items.append(driver)
            seen.add(str(driver.get("id", "")))
    for driver in getattr(app, "drivers", []) or []:
        did = str(driver.get("id", ""))
        if did in seen:
            continue
        cat = str(driver.get("categoria_veiculo") or driver.get("categoria") or "").lower()
        if tipo and cat and (tipo in cat or cat in tipo):
            items.append(driver)
            seen.add(did)
    return items


def vehicle_reservations(app, vehicle):
    vid = str(vehicle.get("id", ""))
    tipo = normalize_vehicle_type(vehicle.get("tipo_veiculo", "")).lower()
    placa = str(vehicle.get("placa", "")).lower()
    display = vehicle_display_name(vehicle).lower()
    items = []
    for reservation in getattr(app, "reservations", []) or []:
        if str(reservation.get("vehicle_id", "")) == vid:
            items.append(reservation)
            continue
        cat = str(reservation.get("categoria") or reservation.get("tipo_veiculo") or reservation.get("tipo", "")).lower()
        veiculo_field = str(reservation.get("veiculo", "")).lower()
        if tipo and cat and (tipo in cat or cat in tipo):
            items.append(reservation)
            continue
        if placa and placa in veiculo_field:
            items.append(reservation)
            continue
        if display and display.split("(")[0].strip() in str(reservation.get("trajeto", "")).lower():
            continue
    return items


def vehicle_stats(app, vehicle):
    reservations = vehicle_reservations(app, vehicle)
    total = len(reservations)
    done = cancelled = pending = 0
    for item in reservations:
        status = str(item.get("status", "")).strip().lower().replace("í", "i")
        if status in DONE_STATUSES:
            done += 1
        elif status in CANCEL_STATUSES:
            cancelled += 1
        else:
            pending += 1
    return {
        "total_reservas": total,
        "reservas_concluidas": done,
        "reservas_pendentes": pending,
        "reservas_canceladas": cancelled,
        "rede": is_network_vehicle(vehicle),
        "portal_publicado": bool(vehicle.get("portal_publicado")),
        "motoristas_vinculados": len(linked_drivers(app, vehicle)),
    }


def list_summary(app):
    vehicles = list_vehicles(app, include_inactive=True)
    active = sum(1 for v in vehicles if str(v.get("status", "")).lower() == "ativo")
    inactive = sum(1 for v in vehicles if str(v.get("status", "")).lower() in {"inativo", "manutencao"})
    network = sum(1 for v in vehicles if is_network_vehicle(v))
    published = sum(1 for v in vehicles if v.get("portal_publicado"))
    return {
        "total": len(vehicles),
        "ativos": active,
        "inativos": inactive,
        "rede": network,
        "publicados": published,
    }


def list_drivers_for_select(app):
    rows = []
    for driver in getattr(app, "drivers", []) or []:
        rows.append({"id": driver.get("id", ""), "nome": driver.get("nome", ""), "label": f'{driver.get("nome", "")} ({driver.get("id", "")})'})
    return rows
