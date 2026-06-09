"""Camada unificada: sessoes, senhas, RBAC e auditoria dos portais."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

try:
    import bcrypt

    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False

USER_TYPE_DRIVER = "driver"
USER_TYPE_COMPANY = "company"
USER_TYPE_PARTNER = "partner"

SESSION_TTL_DRIVER = timedelta(hours=8)
SESSION_TTL_COMPANY = timedelta(hours=12)
SESSION_TTL_PARTNER = timedelta(hours=8)
ACTIVATION_TTL = timedelta(hours=72)

MAX_EVENT_LOG = 500

PORTAL_REGISTRY = {
    USER_TYPE_DRIVER: {"port": 8765, "enabled": True, "label": "Portal Motorista"},
    USER_TYPE_COMPANY: {"port": 8766, "enabled": True, "label": "Portal Empresa"},
    USER_TYPE_PARTNER: {"port": 8767, "enabled": True, "label": "Portal da Rede"},
}

PARTNER_PERMISSIONS = {
    "Administrador": {
        "dashboard",
        "reservations",
        "commissions",
        "contributors",
        "links",
        "profile",
        "export",
        "logout",
    },
    "Operacional": {
        "dashboard",
        "reservations",
        "contributors",
        "links",
        "profile",
        "logout",
    },
    "Financeiro": {
        "dashboard",
        "commissions",
        "export",
        "profile",
        "logout",
    },
}

COMPANY_PERMISSIONS = {
    "Administrador da Empresa": {
        "dashboard",
        "history",
        "request",
        "approve",
        "calculator",
        "vehicles",
        "hotels",
        "airports",
        "locations",
        "coverage",
        "users",
        "cost_centers",
        "passengers",
        "finance",
        "reports",
        "export",
        "logout",
    },
    "Gestor": {
        "dashboard",
        "history",
        "request",
        "approve",
        "calculator",
        "vehicles",
        "hotels",
        "airports",
        "locations",
        "coverage",
        "cost_centers",
        "passengers",
        "reports",
        "logout",
    },
    "Financeiro": {
        "dashboard",
        "history",
        "calculator",
        "vehicles",
        "cost_centers",
        "finance",
        "reports",
        "export",
        "logout",
    },
    "Solicitante": {
        "dashboard",
        "history",
        "request",
        "calculator",
        "vehicles",
        "hotels",
        "airports",
        "locations",
        "passengers",
        "logout",
    },
}

PORTAL_EVENT_TYPES = {
    "portal.driver.login": "Login portal motorista",
    "portal.driver.logout": "Logout portal motorista",
    "portal.driver.password_set": "Senha portal motorista definida",
    "portal.driver.reservation_status": "Status de reserva alterado (motorista)",
    "portal.company.login": "Login portal empresa",
    "portal.company.logout": "Logout portal empresa",
    "portal.company.request_created": "Solicitacao criada no portal empresa",
    "portal.company.request_approved": "Solicitacao aprovada no portal empresa",
    "portal.company.request_rejected": "Solicitacao rejeitada no portal empresa",
    "portal.partner.login": "Login portal da rede",
    "portal.partner.logout": "Logout portal da rede",
}


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def is_password_hash(value):
    raw = str(value or "")
    return raw.startswith("$pbkdf2$") or raw.startswith("$2b$") or raw.startswith("$2a$")


def hash_password(password):
    password = str(password or "")
    if _HAS_BCRYPT:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        return hashed.decode("utf-8")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return f"$pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    stored_hash = str(stored_hash or "")
    password = str(password or "")
    if not stored_hash:
        return False
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        if not _HAS_BCRYPT:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except ValueError:
            return False
    if stored_hash.startswith("$pbkdf2$"):
        try:
            _, salt_hex, digest_hex = stored_hash.split("$", 3)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
            return secrets.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False
    return secrets.compare_digest(password, stored_hash)


def prepare_password_field(value):
    if not value:
        return value
    if is_password_hash(value):
        return value
    return hash_password(value)


def ensure_portal_sessions(app):
    if not hasattr(app, "portal_sessions") or app.portal_sessions is None:
        app.portal_sessions = []
    return app.portal_sessions


def purge_expired_sessions(app):
    sessions = ensure_portal_sessions(app)
    now = _utc_now()
    kept = []
    changed = False
    for session in sessions:
        expires = _parse_iso(session.get("expires_at"))
        if expires and expires < now:
            changed = True
            continue
        kept.append(session)
    if changed:
        app.portal_sessions = kept
    return changed


def create_session(app, user_type, user_id, *, tenant_id="", slug="", perfil="", ttl=None):
    purge_expired_sessions(app)
    if ttl is None:
        if user_type == USER_TYPE_COMPANY:
            ttl = SESSION_TTL_COMPANY
        elif user_type == USER_TYPE_PARTNER:
            ttl = SESSION_TTL_PARTNER
        else:
            ttl = SESSION_TTL_DRIVER
    now = _utc_now()
    session_id = secrets.token_urlsafe(32)
    record = {
        "session_id": session_id,
        "user_type": user_type,
        "user_id": str(user_id),
        "tenant_id": str(tenant_id or ""),
        "slug": str(slug or ""),
        "perfil": str(perfil or ""),
        "created_at": _iso(now),
        "expires_at": _iso(now + ttl),
        "last_activity": _iso(now),
    }
    ensure_portal_sessions(app).append(record)
    return session_id, record


def get_valid_session(app, session_id):
    if not session_id:
        return None
    purge_expired_sessions(app)
    for session in ensure_portal_sessions(app):
        if session.get("session_id") != session_id:
            continue
        expires = _parse_iso(session.get("expires_at"))
        if expires and expires < _utc_now():
            return None
        return session
    return None


def touch_session(app, session_id):
    session = get_valid_session(app, session_id)
    if not session:
        return None
    now = _utc_now()
    session["last_activity"] = _iso(now)
    ut = session.get("user_type")
    if ut == USER_TYPE_COMPANY:
        ttl = SESSION_TTL_COMPANY
    elif ut == USER_TYPE_PARTNER:
        ttl = SESSION_TTL_PARTNER
    else:
        ttl = SESSION_TTL_DRIVER
    session["expires_at"] = _iso(now + ttl)
    return session


def revoke_session(app, session_id):
    sessions = ensure_portal_sessions(app)
    before = len(sessions)
    app.portal_sessions = [item for item in sessions if item.get("session_id") != session_id]
    return len(app.portal_sessions) < before


def company_permissions(perfil):
    return sorted(COMPANY_PERMISSIONS.get(perfil or "Solicitante", COMPANY_PERMISSIONS["Solicitante"]))


def company_can(perfil, action):
    return action in COMPANY_PERMISSIONS.get(perfil or "Solicitante", set())


def partner_permissions(perfil):
    return sorted(PARTNER_PERMISSIONS.get(perfil or "Operacional", PARTNER_PERMISSIONS["Operacional"]))


def partner_can(perfil, action):
    return action in PARTNER_PERMISSIONS.get(perfil or "Operacional", set())


def next_driver_id(drivers):
    numbers = []
    for driver in drivers:
        driver_id = str(driver.get("id", ""))
        if driver_id.startswith("drv-"):
            try:
                numbers.append(int(driver_id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"drv-{max(numbers, default=0) + 1:04d}"


def next_event_id(app):
    numbers = []
    for item in getattr(app, "event_log", []):
        event_id = str(item.get("id", ""))
        if event_id.startswith("evt-"):
            try:
                numbers.append(int(event_id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"evt-{max(numbers, default=0) + 1:04d}"


def log_portal_event(app, event_type, resumo, *, user_type="", user_id="", referencia_id="", origem="portal", payload=None):
    if not hasattr(app, "event_log"):
        app.event_log = []
    event = {
        "id": next_event_id(app),
        "tipo": event_type,
        "titulo": PORTAL_EVENT_TYPES.get(event_type, event_type),
        "resumo": resumo,
        "origem": origem,
        "referencia_id": referencia_id,
        "user_type": user_type,
        "user_id": user_id,
        "payload": dict(payload or {}),
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    app.event_log.insert(0, event)
    app.event_log = app.event_log[:MAX_EVENT_LOG]
    return event


def generate_activation_token(driver):
    token = secrets.token_urlsafe(32)
    driver["activation_token"] = token
    driver["activation_expires_at"] = _iso(_utc_now() + ACTIVATION_TTL)
    return token


def activation_token_valid(driver, token):
    if not token or not driver:
        return False
    if str(driver.get("activation_token", "")) != str(token):
        return False
    expires = _parse_iso(driver.get("activation_expires_at"))
    if expires and expires < _utc_now():
        return False
    return True


def clear_activation_token(driver):
    driver.pop("activation_token", None)
    driver.pop("activation_expires_at", None)


def driver_has_password(driver):
    return bool(driver.get("password_hash")) and bool(driver.get("portal_ativo"))


def set_driver_password(driver, password):
    driver["password_hash"] = hash_password(password)
    driver["portal_ativo"] = True
    clear_activation_token(driver)


def verify_driver_password(driver, password):
    if not driver:
        return False
    stored = driver.get("password_hash", "")
    if stored:
        return verify_password(password, stored)
    return False


def find_driver_by_id(app, driver_id):
    driver_id = str(driver_id or "")
    for driver in getattr(app, "drivers", []):
        if str(driver.get("id", "")) == driver_id:
            return driver
    return None


def find_driver_by_name(app, name):
    name = str(name or "").strip()
    for driver in getattr(app, "drivers", []):
        if str(driver.get("nome", "")).strip() == name:
            return driver
    return None


def normalize_driver_record(driver, drivers=None):
    driver = dict(driver or {})
    if not str(driver.get("id", "")).startswith("drv-"):
        driver["id"] = next_driver_id(drivers or [])
    driver.setdefault("portal_ativo", bool(driver.get("password_hash")))
    if driver.get("portal_ativo") and not driver.get("password_hash"):
        driver["portal_ativo"] = False
    if not driver.get("password_hash") and not driver.get("activation_token"):
        generate_activation_token(driver)
    return driver


def ensure_driver_ids(app):
    changed = False
    drivers = []
    for driver in getattr(app, "drivers", []):
        item = dict(driver)
        if not str(item.get("id", "")).startswith("drv-"):
            item["id"] = next_driver_id(drivers)
            changed = True
        if not item.get("password_hash") and not item.get("activation_token"):
            generate_activation_token(item)
            changed = True
        drivers.append(item)
    if changed:
        app.drivers = drivers
    return changed


def migrate_reservation_driver_ids(app):
    changed = False
    for reservation in getattr(app, "reservations", []):
        if reservation.get("driver_id"):
            continue
        motorista = str(reservation.get("motorista", "")).strip()
        if not motorista or motorista == "-":
            continue
        driver = find_driver_by_name(app, motorista)
        if driver:
            reservation["driver_id"] = driver.get("id", "")
            changed = True
    return changed


def migrate_company_passwords(app):
    changed = False
    for client in getattr(app, "clients", []):
        if client.get("tipo_pessoa") != "juridica":
            continue
        users = []
        for user in client.get("usuarios") or []:
            item = dict(user)
            senha = item.get("senha", "")
            if senha and not is_password_hash(senha):
                item["senha"] = hash_password(senha)
                changed = True
            users.append(item)
        if users:
            client["usuarios"] = users
    return changed


def ensure_portal_security(app):
    changed = False
    changed |= ensure_driver_ids(app)
    changed |= migrate_reservation_driver_ids(app)
    changed |= migrate_company_passwords(app)
    changed |= purge_expired_sessions(app)
    return changed


def driver_reservations_for(app, driver):
    driver_ids = _driver_identity_ids(driver)
    items = []
    for reservation in getattr(app, "reservations", []):
        if _reservation_driver_ids(reservation) & driver_ids:
            items.append(reservation)
    return items


def _driver_identity_ids(driver):
    ids = set()
    for key in ("id", "uuid", "supabase_id"):
        value = str((driver or {}).get(key, "")).strip()
        if value:
            ids.add(value)
    return ids


def _reservation_driver_ids(reservation):
    ids = set()
    for key in ("driver_id", "driver_uuid"):
        value = str((reservation or {}).get(key, "")).strip()
        if value:
            ids.add(value)
    return ids


def reservation_belongs_to_driver(reservation, driver):
    return bool(_reservation_driver_ids(reservation) & _driver_identity_ids(driver))


def active_portal_drivers(app):
    return [
        driver
        for driver in getattr(app, "drivers", [])
        if driver_has_password(driver) and str(driver.get("frota", "Ativo")).lower() in {"ativo", "homologado", "operando"}
    ]
