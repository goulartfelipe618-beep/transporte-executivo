import json
import os

from .geography import migrate_legacy_coverage

STATE_FILE = os.path.join("data", "app_state.json")
STATE_KEYS = (
    "reservations",
    "clients",
    "drivers",
    "vehicles",
    "operational_points",
    "hotels",
    "airports",
    "networks",
    "rede_empresas",
    "partner_networks",
    "network_contributors",
    "network_commissions",
    "contributor_commissions",
    "network_access_logs",
    "audit_log",
    "transport_requests",
    "company_leads",
    "driver_leads",
    "event_log",
    "portal_sessions",
)
LEGACY_KEYS = ("coverage",)


def _load_json_state():
    if not os.path.exists(STATE_FILE):
        return {key: [] for key in STATE_KEYS}

    try:
        with open(STATE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        data = {}

    if data.get("coverage") and not data.get("_geo_migrated"):
        data, _changed = migrate_legacy_coverage(data)
        _persist_raw_state(data)

    payload = {key: list(data.get(key, [])) for key in STATE_KEYS}
    payload["_geo_migrated"] = data.get("_geo_migrated", True)
    payload["_geo_migrated_at"] = data.get("_geo_migrated_at", "")
    return payload


def _require_supabase():
    from .repository.supabase_client import is_configured

    if not is_configured():
        raise RuntimeError("Supabase obrigatorio — configure SUPABASE_URL e chave de API.")


def load_state():
    _require_supabase()
    from .repository.supabase_store import load_state_dict

    remote = load_state_dict()
    if remote is None:
        return {key: [] for key in STATE_KEYS}
    return {key: list(remote.get(key, [])) for key in STATE_KEYS}


def save_state(app):
    _require_supabase()
    from .repository.supabase_store import persist_state

    persist_state(app)

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    payload = {key: list(getattr(app, key, [])) for key in STATE_KEYS}

    existing = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as handle:
                existing = json.load(handle)
        except (json.JSONDecodeError, OSError):
            existing = {}

    payload["_geo_migrated"] = existing.get("_geo_migrated", True)
    payload["_geo_migrated_at"] = existing.get("_geo_migrated_at", "")
    payload["coverage"] = []

    with open(STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _persist_raw_state(data):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def backup_state_keys(app, keys):
    """Atualiza backup JSON apenas das chaves informadas (rapido)."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    existing = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as handle:
                existing = json.load(handle)
        except (json.JSONDecodeError, OSError):
            existing = {}
    for key in keys:
        if key in STATE_KEYS:
            existing[key] = list(getattr(app, key, []) or [])
    existing["_geo_migrated"] = existing.get("_geo_migrated", True)
    existing["_geo_migrated_at"] = existing.get("_geo_migrated_at", "")
    existing.setdefault("coverage", [])
    with open(STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(existing, handle, ensure_ascii=False, indent=2)
