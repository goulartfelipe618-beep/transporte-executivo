"""Geolocalizador — links de rastreio vinculados a reservas."""
from __future__ import annotations

import math
from datetime import datetime

from app.tracking_links import (
    STATUS_ACTIVE,
    STATUS_ENDED,
    STATUS_LABELS,
    STATUS_WAITING,
    TARGET_CLIENTE,
    TARGET_LABELS,
    TARGET_MOTORISTA,
    ensure_tracking_links_loaded,
    new_tracking_token,
    normalize_tracking_link,
    save_tracking_links,
    tracking_public_url,
)

from .reservation_service import find_reservation, reservation_numero_slug

CLOSED_STATUSES = {"concluida", "concluido", "cancelada", "cancelado"}


def _rows(runtime):
    ensure_tracking_links_loaded(runtime)
    return list(getattr(runtime, "tracking_links", []) or [])


def _next_tracking_id(runtime):
    from app.tracking_links import _next_link_id

    return _next_link_id(_rows(runtime))


def _persist(runtime):
    save_tracking_links(runtime)


def _parse_reservation_datetime(reservation):
    data_raw = str(reservation.get("data", "") or "").strip()
    hora_raw = str(
        reservation.get("hora")
        or reservation.get("hora_inicio")
        or reservation.get("hora_ida")
        or ""
    ).strip()
    if not data_raw:
        return None
    for date_fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            date_part = datetime.strptime(data_raw[:10], date_fmt).date()
            break
        except ValueError:
            date_part = None
    if not date_part:
        return None
    if hora_raw and len(hora_raw) >= 4:
        for time_fmt in ("%H:%M", "%H:%M:%S"):
            try:
                time_part = datetime.strptime(hora_raw[:8], time_fmt).time()
                return datetime.combine(date_part, time_part)
            except ValueError:
                pass
    return datetime.combine(date_part, datetime.max.time().replace(microsecond=0))


def is_reservation_trackable(reservation, *, now=None):
    if not reservation:
        return False
    status = str(reservation.get("status", "")).strip().lower().replace("í", "i")
    if status in CLOSED_STATUSES:
        return False
    when = _parse_reservation_datetime(reservation)
    ref = now or datetime.now()
    if when and when < ref:
        return False
    return True


def eligible_reservations(runtime):
    now = datetime.now()
    rows = []
    seen = set()
    for reservation in getattr(runtime, "reservations", []) or []:
        if not is_reservation_trackable(reservation, now=now):
            continue
        numero = str(reservation.get("numero", "")).strip()
        res_id = str(reservation.get("id", "")).strip()
        key = res_id or reservation_numero_slug(numero)
        if not key or key in seen:
            continue
        seen.add(key)
        when = _parse_reservation_datetime(reservation)
        rows.append(
            {
                "id": res_id,
                "numero": numero,
                "cliente": str(reservation.get("cliente", "") or "").strip(),
                "trajeto": str(reservation.get("trajeto", "") or "").strip(),
                "data": str(reservation.get("data", "") or "").strip(),
                "hora": str(reservation.get("hora", "") or reservation.get("hora_inicio", "") or "").strip(),
                "tipo": str(reservation.get("tipo", "") or "").strip(),
                "motorista": str(reservation.get("motorista", "") or "").strip(),
                "when_label": when.strftime("%d/%m/%Y %H:%M") if when else str(reservation.get("data", "")),
            }
        )
    rows.sort(key=lambda row: row.get("when_label", ""))
    return rows


def link_display(item, *, public_base=""):
    target = str(item.get("target_type", ""))
    status = str(item.get("status", STATUS_WAITING))
    last = item.get("last_position") or {}
    return {
        **item,
        "target_label": TARGET_LABELS.get(target, target),
        "status_label": STATUS_LABELS.get(status, status),
        "public_url": tracking_public_url(item.get("token", ""), public_base),
        "tracking_domain": tracking_public_url(item.get("token", "")).split("/rastreio/")[0],
        "is_live": status == STATUS_ACTIVE,
        "waiting_start": status == STATUS_WAITING,
        "has_position": bool(last.get("lat") and last.get("lng")),
        "positions_count": len(item.get("positions") or []),
    }


def list_links(runtime, *, public_base=""):
    return [link_display(item, public_base=public_base) for item in _rows(runtime)]


def list_summary(runtime):
    rows = list_links(runtime)
    return {
        "total": len(rows),
        "ativos": sum(1 for row in rows if row.get("status") == STATUS_ACTIVE),
        "aguardando": sum(1 for row in rows if row.get("status") == STATUS_WAITING),
        "encerrados": sum(1 for row in rows if row.get("status") == STATUS_ENDED),
    }


def find_link_by_id(runtime, link_id):
    link_id = str(link_id or "").strip()
    for item in _rows(runtime):
        if str(item.get("id")) == link_id:
            return link_display(item)
    return None


def find_link_by_token(runtime, token):
    token = str(token or "").strip()
    for item in _rows(runtime):
        if str(item.get("token")) == token:
            return item
    return None


def find_reservation_for_link(runtime, link):
    reservation_id = str(link.get("reservation_id", "")).strip()
    numero = str(link.get("reservation_numero", "")).strip()
    if reservation_id:
        for reservation in getattr(runtime, "reservations", []) or []:
            if str(reservation.get("id", "")) == reservation_id:
                return reservation
    if numero:
        return find_reservation(runtime, numero)
    return None


def validate_create_form(runtime, form_data):
    errors = []
    reservation_ref = str(form_data.get("reservation_id", "")).strip()
    target_type = str(form_data.get("target_type", "")).strip().lower()
    if not reservation_ref:
        errors.append("Selecione uma reserva.")
    if target_type not in {TARGET_CLIENTE, TARGET_MOTORISTA}:
        errors.append("Informe quem sera rastreado: Cliente ou Motorista.")
    reservation = None
    if reservation_ref and not errors:
        reservation = next(
            (
                row
                for row in getattr(runtime, "reservations", []) or []
                if str(row.get("id", "")) == reservation_ref
                or reservation_numero_slug(str(row.get("numero", ""))) == reservation_numero_slug(reservation_ref)
            ),
            None,
        )
        if not reservation:
            errors.append("Reserva nao encontrada.")
        elif not is_reservation_trackable(reservation):
            errors.append("Esta reserva ja passou ou esta concluida/cancelada.")
    return errors, reservation, target_type


def create_link(runtime, form_data, *, created_by=""):
    errors, reservation, target_type = validate_create_form(runtime, form_data)
    if errors:
        return None, errors
    ensure_tracking_links_loaded(runtime)
    item = normalize_tracking_link(
        {
            "id": _next_tracking_id(runtime),
            "token": new_tracking_token(),
            "reservation_id": str(reservation.get("id", "")),
            "reservation_numero": str(reservation.get("numero", "")),
            "target_type": target_type,
            "cliente_nome": str(form_data.get("cliente_nome", "") or reservation.get("cliente", "")).strip(),
            "telefone": str(form_data.get("telefone", "") or reservation.get("contato", "")).strip(),
            "observacoes": str(form_data.get("observacoes", "")).strip(),
            "status": STATUS_WAITING,
            "created_by": created_by,
            "positions": [],
            "last_position": {},
            "summary": {},
        }
    )
    runtime.tracking_links.insert(0, item)
    _persist(runtime)
    return item, []


def mark_communicated(runtime, link_id):
    raw = next((row for row in _rows(runtime) if str(row.get("id")) == str(link_id)), None)
    if not raw:
        return None, ["Link nao encontrado."]
    raw["communicated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    _persist(runtime)
    return link_display(raw), []


def start_trip(runtime, token):
    raw = find_link_by_token(runtime, token)
    if not raw:
        return None, "Link invalido."
    if raw.get("status") == STATUS_ENDED:
        return None, "Esta viagem ja foi encerrada."
    raw["status"] = STATUS_ACTIVE
    raw["started_at"] = datetime.now().isoformat(timespec="seconds")
    _persist(runtime)
    return raw, ""


def _haversine_km(a, b):
    lat1, lng1 = float(a["lat"]), float(a["lng"])
    lat2, lng2 = float(b["lat"]), float(b["lng"])
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    x = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def _recompute_summary(raw):
    positions = list(raw.get("positions") or [])
    summary = dict(raw.get("summary") or {})
    if len(positions) >= 2:
        distance = 0.0
        for index in range(1, len(positions)):
            distance += _haversine_km(positions[index - 1], positions[index])
        summary["distance_km"] = round(distance, 2)
    if raw.get("started_at") and raw.get("ended_at"):
        try:
            start = datetime.fromisoformat(str(raw["started_at"]))
            end = datetime.fromisoformat(str(raw["ended_at"]))
            summary["duration_min"] = max(0, int((end - start).total_seconds() // 60))
        except ValueError:
            pass
    if positions:
        first = positions[0]
        last = positions[-1]
        summary["start_label"] = f"{first.get('lat', '')}, {first.get('lng', '')}"
        summary["end_label"] = f"{last.get('lat', '')}, {last.get('lng', '')}"
    raw["summary"] = summary


def append_position(runtime, token, payload):
    raw = find_link_by_token(runtime, token)
    if not raw:
        return None, "Link invalido."
    if raw.get("status") != STATUS_ACTIVE:
        return None, "A viagem ainda nao foi iniciada."
    try:
        lat = float(payload.get("lat"))
        lng = float(payload.get("lng"))
    except (TypeError, ValueError):
        return None, "Coordenadas invalidas."
    point = {
        "lat": lat,
        "lng": lng,
        "accuracy": payload.get("accuracy"),
        "speed": payload.get("speed"),
        "heading": payload.get("heading"),
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    raw.setdefault("positions", []).append(point)
    raw["positions"] = raw["positions"][-500:]
    raw["last_position"] = point
    _recompute_summary(raw)
    _persist(runtime)
    return point, ""


def end_trip(runtime, token_or_id, *, by_admin=False):
    token_or_id = str(token_or_id or "").strip()
    raw = find_link_by_token(runtime, token_or_id)
    if not raw:
        raw = next((row for row in _rows(runtime) if str(row.get("id")) == token_or_id), None)
    if not raw:
        return None, ["Link nao encontrado."]
    raw["status"] = STATUS_ENDED
    raw["ended_at"] = datetime.now().isoformat(timespec="seconds")
    _recompute_summary(raw)
    _persist(runtime)
    return link_display(raw), []


def delete_link(runtime, link_id):
    link_id = str(link_id or "").strip()
    before = len(_rows(runtime))
    runtime.tracking_links = [row for row in _rows(runtime) if str(row.get("id")) != link_id]
    if len(runtime.tracking_links) == before:
        return False, ["Link nao encontrado."]
    _persist(runtime)
    return True, []


def live_payload(runtime, link_id):
    item = find_link_by_id(runtime, link_id)
    if not item:
        return None
    reservation = find_reservation_for_link(runtime, item)
    return {
        "id": item.get("id"),
        "status": item.get("status"),
        "status_label": item.get("status_label"),
        "target_type": item.get("target_type"),
        "target_label": item.get("target_label"),
        "last_position": item.get("last_position") or {},
        "positions_count": item.get("positions_count"),
        "started_at": item.get("started_at"),
        "reservation": {
            "numero": item.get("reservation_numero"),
            "cliente": (reservation or {}).get("cliente", item.get("cliente_nome")),
            "trajeto": (reservation or {}).get("trajeto", ""),
            "motorista": (reservation or {}).get("motorista", ""),
        },
    }
