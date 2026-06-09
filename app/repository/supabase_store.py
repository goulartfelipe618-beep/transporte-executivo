"""Persistencia central Supabase — leitura/gravacao de todas as colecoes."""
from __future__ import annotations

import json
import os
from copy import deepcopy

from ..storage import STATE_FILE, STATE_KEYS
from . import supabase_client as db
from .supabase_mappers import (
    COLLECTION_TABLE,
    RefResolver,
    TO_ROW,
    from_catalog_row,
    from_company_user_row,
    from_db_row,
    to_catalog_row,
    to_company_row,
    to_company_user_row,
    to_event_log_row,
    to_master_client_row,
)

RESOLVER_COLLECTIONS = {
    "partner_networks",
    "network_contributors",
    "transport_requests",
    "reservations",
    "network_commissions",
    "contributor_commissions",
    "audit_log",
}

IMPORT_ORDER = [
    "partner_networks",
    "network_contributors",
    "drivers",
    "vehicles",
    "operational_points",
    "transport_requests",
    "reservations",
    "network_commissions",
    "contributor_commissions",
    "audit_log",
    "company_leads",
    "driver_leads",
    "event_log",
    "network_access_logs",
    "portal_sessions",
]

CATALOG_COLLECTIONS = {"hotels": "hotels", "airports": "airports", "networks": "networks"}

SINGLE_ARG_MAPPERS = {"drivers", "vehicles", "operational_points", "company_leads", "driver_leads"}


def _invoke_mapper(mapper, collection, item, resolver):
    if collection == "event_log":
        legacy = item.get("id") or "evt-fast"
        return to_event_log_row(item, legacy_override=legacy)
    if collection in SINGLE_ARG_MAPPERS:
        return mapper(item)
    return mapper(item, resolver)


def _table_for(collection):
    return COLLECTION_TABLE.get(collection)


RESOLVER_TABLES_BY_COLLECTION = {
    "partner_networks": ("partner_networks",),
    "network_contributors": ("partner_networks", "network_contributors"),
    "transport_requests": ("partner_networks", "network_contributors"),
    "reservations": ("partner_networks", "network_contributors", "transport_requests"),
    "network_commissions": ("partner_networks", "network_contributors", "reservations", "transport_requests"),
    "contributor_commissions": ("partner_networks", "network_contributors", "reservations"),
    "audit_log": ("partner_networks", "reservations"),
    "portal_sessions": ("partner_networks", "drivers"),
    "network_access_logs": ("partner_networks", "network_contributors"),
}

DEFAULT_RESOLVER_TABLES = (
    "partner_networks",
    "network_contributors",
    "drivers",
    "vehicles",
    "companies",
    "master_clients",
    "transport_requests",
    "reservations",
)


def _build_resolver(tables=None):
    resolver = RefResolver()
    for table in tables or DEFAULT_RESOLVER_TABLES:
        for row in db.select_all(table):
            legacy = row.get("legacy_admin_id")
            if legacy:
                resolver.register(legacy, row.get("id"))
    return resolver


def _hydrate_company_users(items):
    if not db.is_configured():
        return
    users_by_company = {}
    for row in db.select_all("company_users"):
        company_uuid = str(row.get("company_id") or "")
        if not company_uuid:
            continue
        users_by_company.setdefault(company_uuid, []).append(from_company_user_row(row))
    for item in items:
        if item.get("tipo_pessoa") != "juridica":
            continue
        company_uuid = str(item.get("uuid") or "")
        if company_uuid and company_uuid in users_by_company:
            item["usuarios"] = users_by_company[company_uuid]


def _load_clients():
    items = []
    for row in db.select_all("companies"):
        item = from_db_row(row)
        item["tipo_pessoa"] = "juridica"
        items.append(item)
    for row in db.select_all("master_clients"):
        item = from_db_row(row)
        item["tipo_pessoa"] = item.get("tipo_pessoa", "fisica")
        items.append(item)
    _hydrate_company_users(items)
    return items


def _save_clients(clients):
    for item in clients or []:
        if item.get("tipo_pessoa") == "juridica" or item.get("cnpj") or item.get("razao_social"):
            payload = {key: value for key, value in item.items() if key != "usuarios"}
            row = to_company_row(payload)
            saved = db.upsert_row("companies", row)
            if saved and saved.get("id"):
                item["uuid"] = saved["id"]
        else:
            row = to_master_client_row(item)
            saved = db.upsert_row("master_clients", row)
            if saved and saved.get("id"):
                item["uuid"] = saved["id"]


def load_company_users(company_uuid):
    if not db.is_configured() or not company_uuid:
        return []
    rows = db.select_all("company_users", filters={"company_id": company_uuid})
    return [from_company_user_row(row) for row in rows]


def upsert_company_user(item, *, company_uuid, company_legacy_id=None):
    if not db.is_configured():
        return None
    row = to_company_user_row(item, company_uuid=company_uuid, company_legacy_id=company_legacy_id)
    saved = db.upsert_row("company_users", row)
    if saved and saved.get("id"):
        item["uuid"] = saved["id"]
    return saved


def delete_company_user_row(*, company_uuid, legacy_user_id=None, user_uuid=None, company_legacy_id=None):
    if not db.is_configured():
        return False
    filters = {"company_id": company_uuid}
    if user_uuid:
        filters["id"] = user_uuid
    elif legacy_user_id:
        from .supabase_mappers import company_user_storage_legacy

        filters["legacy_admin_id"] = company_user_storage_legacy(company_legacy_id, legacy_user_id)
    else:
        return False
    db.delete_rows("company_users", filters)
    return True


def _load_catalog(collection_key):
    rows = db.select_all("master_catalog_items", filters={"collection_key": collection_key})
    return [from_catalog_row(row) for row in rows]


def _save_catalog(collection_key, items):
    for item in items or []:
        row = to_catalog_row(item, collection_key)
        existing = db.select_one("master_catalog_items", {
            "collection_key": collection_key,
            "legacy_admin_id": item.get("id"),
        })
        if existing:
            db.patch_rows("master_catalog_items", {"id": existing["id"]}, {"payload": item})
        else:
            db.insert_row("master_catalog_items", row)


def load_collection(collection):
    if collection == "clients":
        return _load_clients()
    if collection in CATALOG_COLLECTIONS:
        return _load_catalog(CATALOG_COLLECTIONS[collection])
    table = _table_for(collection)
    if not table:
        return []
    rows = db.select_all(table, order="created_at.desc")
    return [from_db_row(row) for row in rows]


def _upsert_row_idempotent(table, row, *, conflict_key="legacy_admin_id"):
    """Upsert por legacy_admin_id — evita 409 quando row.id (uuid) diverge do registro existente."""
    legacy = row.get(conflict_key)
    if legacy:
        existing = db.select_one(table, filters={conflict_key: legacy})
        if existing:
            patch_payload = {key: value for key, value in row.items() if key != "id"}
            patched = db.patch_rows(table, {conflict_key: legacy}, patch_payload)
            if patched:
                return patched[0]
            return existing
    return db.upsert_row(table, row, on_conflict=conflict_key)


def upsert_collection_items(collection, items):
    """Grava apenas os itens informados (sem varrer/deletar colecoes inteiras)."""
    items = [item for item in (items or []) if isinstance(item, dict)]
    if not items:
        return {"ok": True, "count": 0}
    if not db.is_configured():
        return {"ok": False, "error": "supabase_not_configured"}
    if collection == "clients":
        _save_clients(items)
        return {"ok": True, "count": len(items)}
    if collection in CATALOG_COLLECTIONS:
        _save_catalog(CATALOG_COLLECTIONS[collection], items)
        return {"ok": True, "count": len(items)}
    table = _table_for(collection)
    mapper = TO_ROW.get(collection)
    if not table or not mapper:
        return {"ok": False, "error": f"no_mapper_for_{collection}"}
    resolver = _build_resolver(RESOLVER_TABLES_BY_COLLECTION.get(collection, DEFAULT_RESOLVER_TABLES))
    saved_count = 0
    for index, item in enumerate(items):
        if collection == "event_log" and not item.get("id"):
            item = {**item, "id": f"evt-fast-{index + 1:04d}"}
        row = _invoke_mapper(mapper, collection, item, resolver)
        if collection == "network_commissions":
            saved = _upsert_row_idempotent(table, row)
        else:
            saved = db.upsert_row(table, row)
        if saved:
            item["uuid"] = saved.get("id")
            resolver.register(item.get("id"), saved.get("id"))
            saved_count += 1
    return {"ok": True, "count": saved_count}


def persist_network_reservation_bundle(app, *, treq, reservation, net_com, ccom=None, audit=None, event=None):
    """Persistencia rapida do POST reserve — somente entidades da reserva."""
    if not db.is_configured():
        return {"ok": False, "error": "supabase_not_configured"}
    results = {}
    for collection, payload in (
        ("transport_requests", [treq]),
        ("reservations", [reservation]),
        ("network_commissions", [net_com]),
        ("contributor_commissions", [ccom] if ccom else []),
        ("audit_log", [audit] if audit else []),
        ("event_log", [event] if event else []),
    ):
        if not payload or not payload[0]:
            continue
        results[collection] = upsert_collection_items(collection, payload)
    return {"ok": True, "results": results}


def save_collection(collection, items):
    return upsert_collection_items(collection, items or [])


def load_state_dict():
    if not db.is_configured():
        return None
    payload = {key: load_collection(key) for key in STATE_KEYS}
    meta = db.select_one("settings", {"chave": "app_state_meta"})
    if meta and isinstance(meta.get("valor"), dict):
        payload["_geo_migrated"] = meta["valor"].get("_geo_migrated", True)
        payload["_geo_migrated_at"] = meta["valor"].get("_geo_migrated_at", "")
    else:
        payload["_geo_migrated"] = True
        payload["_geo_migrated_at"] = ""
    payload["coverage"] = []
    rede = payload.get("rede_empresas") or []
    if rede and not payload.get("partner_networks"):
        payload["partner_networks"] = rede
    return payload


def persist_state(app):
    if not db.is_configured():
        return False
    resolver = _build_resolver()
    for key in STATE_KEYS:
        items = list(getattr(app, key, []) or [])
        if key == "clients":
            _save_clients(items)
            continue
        if key in CATALOG_COLLECTIONS:
            _save_catalog(CATALOG_COLLECTIONS[key], items)
            continue
        if key == "rede_empresas":
            continue
        table = _table_for(key)
        mapper = TO_ROW.get(key)
        if not table or not mapper:
            continue
        existing = {row.get("legacy_admin_id"): row for row in db.select_all(table) if row.get("legacy_admin_id")}
        seen = set()
        for index, item in enumerate(items):
            if key == "event_log":
                legacy = item.get("id") or f"evt-{index + 1:04d}"
                if legacy in seen:
                    legacy = f"{legacy}-{index + 1:04d}"
                seen.add(legacy)
                item = {**item, "id": legacy}
            row = _invoke_mapper(mapper, key, item, resolver)
            if key == "network_commissions":
                saved = _upsert_row_idempotent(table, row)
            else:
                saved = db.upsert_row(table, row)
            if saved:
                item["uuid"] = saved.get("id")
                resolver.register(item.get("id"), saved.get("id"))
                existing.pop(item.get("id"), None)
        for legacy_id, stale in existing.items():
            if legacy_id:
                db.delete_rows(table, {"legacy_admin_id": legacy_id})

    meta = {
        "_geo_migrated": True,
        "_geo_migrated_at": "",
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as handle:
                local = json.load(handle)
            meta["_geo_migrated"] = local.get("_geo_migrated", True)
            meta["_geo_migrated_at"] = local.get("_geo_migrated_at", "")
        except (json.JSONDecodeError, OSError):
            pass
    db.upsert_row("settings", {"chave": "app_state_meta", "valor": meta, "descricao": "Metadados migracao geo"}, on_conflict="chave")
    return True


def import_json_file(path=None):
    path = path or STATE_FILE
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    resolver = RefResolver()

    partners = list(data.get("partner_networks") or [])
    for legacy in data.get("rede_empresas") or []:
        if not any(p.get("id") == legacy.get("id") for p in partners):
            partners.append(legacy)
    for item in partners:
        row = TO_ROW["partner_networks"](item, resolver)
        saved = db.upsert_row("partner_networks", row)
        if saved:
            resolver.register(item.get("id"), saved.get("id"))
            item["uuid"] = saved["id"]

    for item in data.get("network_contributors") or []:
        row = TO_ROW["network_contributors"](item, resolver)
        saved = db.upsert_row("network_contributors", row)
        if saved:
            resolver.register(item.get("id"), saved.get("id"))

    from .supabase_mappers import to_driver_row, to_operational_point_row, to_vehicle_row

    for item in data.get("drivers") or []:
        saved = db.upsert_row("drivers", to_driver_row(item))
        if saved:
            resolver.register(item.get("id"), saved.get("id"))
    for item in data.get("vehicles") or []:
        saved = db.upsert_row("vehicles", to_vehicle_row(item))
        if saved:
            resolver.register(item.get("id"), saved.get("id"))
    for item in data.get("operational_points") or []:
        saved = db.upsert_row("operational_points", to_operational_point_row(item))
        if saved:
            resolver.register(item.get("id"), saved.get("id"))

    for item in data.get("transport_requests") or []:
        row = TO_ROW["transport_requests"](item, resolver)
        saved = db.upsert_row("transport_requests", row)
        if saved:
            resolver.register(item.get("id"), saved.get("id"))

    for item in data.get("reservations") or []:
        row = TO_ROW["reservations"](item, resolver)
        saved = db.upsert_row("reservations", row)
        if saved:
            resolver.register(item.get("id"), saved.get("id"))

    for item in data.get("network_commissions") or []:
        row = TO_ROW["network_commissions"](item, resolver)
        _upsert_row_idempotent("network_commissions", row)

    for item in data.get("contributor_commissions") or []:
        row = TO_ROW["contributor_commissions"](item, resolver)
        db.upsert_row("contributor_commissions", row)

    for item in data.get("audit_log") or []:
        row = TO_ROW["audit_log"](item, resolver)
        db.upsert_row("audit_log", row)

    for item in data.get("company_leads") or []:
        from .supabase_mappers import to_company_lead_row
        db.upsert_row("company_leads", to_company_lead_row(item))

    for item in data.get("driver_leads") or []:
        from .supabase_mappers import to_driver_lead_row
        db.upsert_row("driver_leads", to_driver_lead_row(item))

    seen_events = set()
    for index, item in enumerate(data.get("event_log") or []):
        legacy = item.get("id") or f"evt-{index + 1:04d}"
        if legacy in seen_events:
            legacy = f"{legacy}-{index + 1:04d}"
        seen_events.add(legacy)
        db.upsert_row("event_log", to_event_log_row(item, legacy_override=legacy))

    for collection_key in CATALOG_COLLECTIONS:
        for item in data.get(collection_key) or []:
            existing = db.select_one("master_catalog_items", {
                "collection_key": collection_key,
                "legacy_admin_id": item.get("id"),
            })
            if existing:
                db.patch_rows("master_catalog_items", {"id": existing["id"]}, {"payload": item})
            else:
                db.insert_row("master_catalog_items", to_catalog_row(item, collection_key))

    for item in data.get("clients") or []:
        if item.get("tipo_pessoa") == "juridica" or item.get("cnpj"):
            saved = db.upsert_row("companies", to_company_row(item))
        else:
            saved = db.upsert_row("master_clients", to_master_client_row(item))
        if saved:
            resolver.register(item.get("id"), saved.get("id"))

    db.upsert_row(
        "settings",
        {
            "chave": "app_state_meta",
            "valor": {
                "_geo_migrated": data.get("_geo_migrated", True),
                "_geo_migrated_at": data.get("_geo_migrated_at", ""),
            },
            "descricao": "Metadados migracao geo",
        },
        on_conflict="chave",
    )
    return count_all_collections()


def count_all_collections():
    counts = {}
    for key in STATE_KEYS:
        if key == "clients":
            counts[key] = db.count_rows("companies") + db.count_rows("master_clients")
        elif key in CATALOG_COLLECTIONS:
            counts[key] = len(db.select_all("master_catalog_items", filters={"collection_key": CATALOG_COLLECTIONS[key]}))
        elif key == "rede_empresas":
            counts[key] = 0
        elif _table_for(key):
            counts[key] = db.count_rows(_table_for(key))
        else:
            counts[key] = 0
    return counts
