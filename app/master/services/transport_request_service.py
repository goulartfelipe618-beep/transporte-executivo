"""CRUD de solicitacoes de transporte — logica extraida de inbound_ui.py e pages.py (sem Tkinter)."""
from __future__ import annotations

from datetime import datetime

from app.platform import (
    ORIGIN_SITE,
    TRANSPORT_REQUEST_STATUSES,
    ensure_platform_collections,
    log_event,
    next_record_id,
    normalize_transport_request,
)

CANCEL_STATUS = "Cancelada"
CONFIRM_STATUS = "Confirmada"
ACTIVE_STATUS = "Recebida"
OPEN_STATUSES = {"Recebida", "Em analise", "Cotada"}


def request_display_name(item):
    nome = str(item.get("nome") or item.get("empresa") or "").strip()
    origem = str(item.get("origem", "")).strip()
    destino = str(item.get("destino", "")).strip()
    trajeto = f"{origem} -> {destino}".strip(" ->")
    if nome and trajeto:
        return f"{nome} — {trajeto}"
    return nome or trajeto or item.get("id", "")


def list_transport_requests(app, *, search="", status="", include_cancelled=True):
    ensure_platform_collections(app)
    items = []
    query = str(search or "").strip().lower()
    status_filter = str(status or "").strip()
    for item in getattr(app, "transport_requests", []) or []:
        item_status = str(item.get("status", "")).strip()
        if not include_cancelled and item_status == CANCEL_STATUS:
            continue
        if status_filter and item_status != status_filter:
            continue
        if query:
            haystack = " ".join(
                [
                    item.get("id", ""),
                    item.get("nome", ""),
                    item.get("empresa", ""),
                    item.get("origem", ""),
                    item.get("destino", ""),
                    item.get("telefone", ""),
                    item.get("email", ""),
                    item.get("status", ""),
                ]
            ).lower()
            if query not in haystack:
                continue
        items.append(item)
    items.sort(key=lambda row: str(row.get("criado_em", "")), reverse=True)
    return items


def find_request_by_id(app, request_id):
    request_id = str(request_id or "")
    for item in getattr(app, "transport_requests", []) or []:
        if str(item.get("id", "")) == request_id:
            return item
    return None


def _build_payload(form_data, *, existing=None):
    existing = existing or {}
    merged = dict(existing)
    for key in (
        "origem",
        "destino",
        "data",
        "hora",
        "empresa",
        "nome",
        "telefone",
        "email",
        "origem_fonte",
        "origem_modo",
        "destino_modo",
        "status",
        "observacoes",
        "passageiros",
        "categoria",
        "company_id",
        "reservation_id",
    ):
        if key in form_data:
            merged[key] = str(form_data.get(key, "")).strip()
    merged["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    return normalize_transport_request(merged)


def create_transport_request(app, form_data):
    ensure_platform_collections(app)
    records = getattr(app, "transport_requests", []) or []
    payload = _build_payload(form_data)
    payload["id"] = next_record_id("treq", records)
    payload["criado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    if not payload.get("origem_fonte"):
        payload["origem_fonte"] = ORIGIN_SITE
    records.insert(0, payload)
    app.transport_requests = records
    log_event(
        app,
        "inbound.manual.created",
        f'Solicitacao criada: {payload.get("id", "")}',
        referencia_id=payload.get("id", ""),
        origem=payload.get("origem_fonte", "painel"),
    )
    if hasattr(app, "save_state"):
        app.save_state()
    return payload


def update_transport_request(app, request_id, form_data):
    item = find_request_by_id(app, request_id)
    if not item:
        raise ValueError("solicitacao_nao_encontrada")
    old_status = item.get("status")
    payload = _build_payload(form_data, existing=item)
    item.update(payload)
    if old_status != item.get("status"):
        log_event(
            app,
            "inbound.status.changed",
            f'Status alterado para {item.get("status")}',
            referencia_id=item.get("id", ""),
        )
    if hasattr(app, "save_state"):
        app.save_state()
    return item


def block_transport_request(app, request_id):
    item = find_request_by_id(app, request_id)
    if not item:
        raise ValueError("solicitacao_nao_encontrada")
    item["status"] = CANCEL_STATUS
    item["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    log_event(app, "inbound.status.changed", "Solicitacao cancelada", referencia_id=item.get("id", ""))
    if hasattr(app, "save_state"):
        app.save_state()
    return item


def activate_transport_request(app, request_id):
    item = find_request_by_id(app, request_id)
    if not item:
        raise ValueError("solicitacao_nao_encontrada")
    if str(item.get("status", "")) == CANCEL_STATUS:
        item["status"] = ACTIVE_STATUS
    else:
        item["status"] = CONFIRM_STATUS
    item["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    log_event(app, "inbound.status.changed", f'Status alterado para {item.get("status")}', referencia_id=item.get("id", ""))
    if hasattr(app, "save_state"):
        app.save_state()
    return item


def linked_reservation(app, item):
    rid = str(item.get("reservation_id", "")).strip()
    if rid:
        for reservation in getattr(app, "reservations", []) or []:
            if str(reservation.get("id", "")) == rid:
                return reservation
    treq_id = str(item.get("id", ""))
    for reservation in getattr(app, "reservations", []) or []:
        if str(reservation.get("transport_request_id", "")) == treq_id:
            return reservation
    return None


def linked_company(app, item):
    company_id = str(item.get("company_id", "")).strip()
    if company_id:
        for client in getattr(app, "clients", []) or []:
            if str(client.get("id", "")) == company_id:
                return client
    empresa = str(item.get("empresa", "")).strip().lower()
    if not empresa:
        return None
    for client in getattr(app, "clients", []) or []:
        names = [
            str(client.get("razao_social", "")).lower(),
            str(client.get("nome_fantasia", "")).lower(),
            str(client.get("nome", "")).lower(),
            str(client.get("empresa", "")).lower(),
        ]
        if empresa in names:
            return client
    return None


def linked_driver(app, item):
    reservation = linked_reservation(app, item)
    if not reservation:
        return None
    motorista = str(reservation.get("motorista", "")).strip()
    driver_id = str(reservation.get("driver_id", "")).strip()
    if driver_id:
        for driver in getattr(app, "drivers", []) or []:
            if str(driver.get("id", "")) == driver_id:
                return driver
    if motorista and motorista != "-":
        for driver in getattr(app, "drivers", []) or []:
            if str(driver.get("nome", "")).strip() == motorista.split(" (drv-")[0].strip():
                return driver
    return None


def linked_vehicle(app, item):
    reservation = linked_reservation(app, item)
    if not reservation:
        return None
    vehicle_id = str(reservation.get("vehicle_id", "")).strip()
    if not vehicle_id:
        return None
    for vehicle in getattr(app, "vehicles", []) or []:
        if str(vehicle.get("id", "")) == vehicle_id:
            return vehicle
    return None


def request_stats(app, item):
    reservation = linked_reservation(app, item)
    return {
        "status": item.get("status", ""),
        "origem_fonte": item.get("origem_fonte", ""),
        "tem_reserva": bool(reservation),
        "reserva_numero": reservation.get("numero", "") if reservation else "",
        "tem_empresa": bool(linked_company(app, item)),
        "tem_motorista": bool(linked_driver(app, item)),
        "tem_veiculo": bool(linked_vehicle(app, item)),
    }


def list_summary(app):
    ensure_platform_collections(app)
    records = getattr(app, "transport_requests", []) or []
    pending = sum(1 for item in records if item.get("status") in {"Recebida", "Em analise"})
    quoted = sum(1 for item in records if item.get("status") == "Cotada")
    confirmed = sum(1 for item in records if item.get("status") == CONFIRM_STATUS)
    cancelled = sum(1 for item in records if item.get("status") == CANCEL_STATUS)
    from_site = sum(1 for item in records if str(item.get("origem_fonte", "")).strip() == ORIGIN_SITE)
    return {
        "total": len(records),
        "pendentes": pending,
        "cotadas": quoted,
        "confirmadas": confirmed,
        "canceladas": cancelled,
        "origem_site": from_site,
    }


def filter_options():
    return {"statuses": TRANSPORT_REQUEST_STATUSES}
