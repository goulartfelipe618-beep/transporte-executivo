"""Enderecos com Ponto Operacional — sem Tkinter."""
from __future__ import annotations

from app.geography import ensure_operational_points, operational_point_label


def operational_point_address_text(point):
    if not point:
        return ""
    nome = str(point.get("nome", "")).strip()
    endereco = str(point.get("endereco", "")).strip()
    cidade = str(point.get("cidade_nome", "")).strip()
    uf = str(point.get("estado_uf", "")).strip()
    location = f"{cidade}/{uf}".strip("/")
    if nome and endereco:
        base = f"{nome} — {endereco}"
    else:
        base = nome or endereco
    if location and base:
        return f"{base} ({location})"
    return base or location


def selectable_operational_points(app):
    ensure_operational_points(app)
    points = []
    for point in app.operational_points:
        if point.get("status") == "Pausado":
            continue
        points.append(point)
    return sorted(points, key=lambda item: operational_point_label(item).lower())


def operational_point_options(app):
    return [
        {
            "id": point.get("id", ""),
            "label": operational_point_label(point),
            "address": operational_point_address_text(point),
        }
        for point in selectable_operational_points(app)
    ]


def find_operational_point(app, point_id):
    if not point_id:
        return None
    for point in getattr(app, "operational_points", []) or []:
        if str(point.get("id")) == str(point_id):
            return point
    return None


def resolve_address_field_from_form(app, form_data, key):
    mode = str(form_data.get(f"{key}_modo", "manual") or "manual").strip().lower()
    if mode == "rede":
        point_id = str(form_data.get(f"{key}_po_id", "") or "").strip()
        point = find_operational_point(app, point_id)
        if not point:
            return "", point_id, "rede"
        return operational_point_address_text(point), point_id, "rede"
    return str(form_data.get(key, "") or "").strip(), "", "manual"


def collect_address_values_from_form(app, form_data, keys):
    payload = {}
    for key in keys:
        text, point_id, mode = resolve_address_field_from_form(app, form_data, key)
        payload[key] = text
        payload[f"{key}_po_id"] = point_id or ""
        payload[f"{key}_modo"] = mode
    return payload
