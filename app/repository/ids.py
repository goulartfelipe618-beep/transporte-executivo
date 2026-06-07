"""IDs padronizados para migracao futura (PostgreSQL/Supabase)."""
from __future__ import annotations

ID_PAD = 6

ENTITY_PREFIXES = {
    "company": "emp",
    "client": "cli",
    "driver": "drv",
    "vehicle": "veh",
    "reservation": "res",
    "operational_point": "op",
    "user": "usr",
    "hotel": "htl",
    "airport": "apt",
    "network": "net",
    "company_lead": "clead",
    "driver_lead": "dlead",
    "transport_request": "treq",
    "event": "evt",
}


def next_entity_id(prefix, records, field="id", pad=ID_PAD):
    numbers = []
    for item in records or []:
        record_id = str(item.get(field, ""))
        if record_id.startswith(f"{prefix}-"):
            suffix = record_id.split("-", 1)[1]
            try:
                numbers.append(int(suffix))
            except ValueError:
                pass
    return f"{prefix}-{max(numbers, default=0) + 1:0{pad}d}"


def _ensure_collection_ids(app, attr, prefix, field="id"):
    changed = False
    items = list(getattr(app, attr, []) or [])
    updated = []
    for item in items:
        row = dict(item)
        current = str(row.get(field, "")).strip()
        if not current.startswith(f"{prefix}-"):
            row[field] = next_entity_id(prefix, updated, field=field)
            changed = True
        updated.append(row)
    if changed:
        setattr(app, attr, updated)
    return changed


def _ensure_reservation_ids(app):
    changed = False
    reservations = list(getattr(app, "reservations", []) or [])
    for reservation in reservations:
        if not str(reservation.get("id", "")).startswith("res-"):
            reservation["id"] = next_entity_id("res", reservations)
            changed = True
    return changed


def _ensure_company_user_ids(app):
    changed = False
    for client in getattr(app, "clients", []):
        if client.get("tipo_pessoa") != "juridica":
            continue
        users = []
        for user in client.get("usuarios") or []:
            row = dict(user)
            if not str(row.get("id", "")).startswith("usr-"):
                row["id"] = next_entity_id("usr", users)
                changed = True
            users.append(row)
        if users:
            client["usuarios"] = users
    return changed


def ensure_entity_ids(app):
    """Garante IDs estaveis em todas as colecoes principais."""
    changed = False
    changed |= _ensure_collection_ids(app, "clients", "cli")
    changed |= _ensure_collection_ids(app, "drivers", "drv")
    changed |= _ensure_collection_ids(app, "vehicles", "veh")
    changed |= _ensure_collection_ids(app, "operational_points", "op")
    changed |= _ensure_collection_ids(app, "hotels", "htl")
    changed |= _ensure_collection_ids(app, "airports", "apt")
    changed |= _ensure_collection_ids(app, "networks", "net")
    changed |= _ensure_reservation_ids(app)
    changed |= _ensure_company_user_ids(app)
    for client in getattr(app, "clients", []):
        if client.get("tipo_pessoa") == "juridica" and not str(client.get("id", "")).startswith("emp-"):
            client["id"] = next_entity_id("emp", getattr(app, "clients", []))
            changed = True
    return changed
