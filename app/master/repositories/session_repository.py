"""Persistencia de sessoes administrativas — Supabase REST + SQLAlchemy async opcional."""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, timezone

from app.repository.supabase_client import delete_rows, insert_row, patch_rows, select_one

TABLE = "master_admin_sessions"
AUDIT_TABLE = "master_login_audit"

_SESSION_CACHE: dict[str, tuple[dict, float]] = {}
_LAST_TOUCH: dict[str, float] = {}
_CACHE_TTL = float(os.environ.get("MASTER_SESSION_CACHE_TTL", "120"))
_TOUCH_DEBOUNCE = float(os.environ.get("MASTER_SESSION_TOUCH_SECONDS", "300"))
_cache_lock = threading.Lock()


def _utcnow():
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def create_session_record(
    *,
    session_id: str,
    admin: dict,
    ip_address: str = "",
    user_agent: str = "",
    max_age_seconds: int,
) -> dict:
    now = _utcnow()
    expires = now + timedelta(seconds=max_age_seconds)
    payload = {
        "id": session_id,
        "admin_id": str(admin.get("id", "")),
        "admin_email": str(admin.get("email", "")),
        "admin_nome": str(admin.get("nome") or "Administrador"),
        "admin_perfil": str(admin.get("perfil") or "Administrador Master"),
        "ip_address": ip_address[:45],
        "user_agent": user_agent[:2000],
        "created_at": _iso(now),
        "last_seen_at": _iso(now),
        "expires_at": _iso(expires),
        "revoked_at": None,
    }
    row = insert_row(TABLE, payload)
    record = row or payload
    _store_session_cache(session_id, record)
    return record


def _store_session_cache(session_id: str, record: dict) -> None:
    if not session_id or not record:
        return
    with _cache_lock:
        _SESSION_CACHE[session_id] = (dict(record), time.monotonic())


def _invalidate_session_cache(session_id: str) -> None:
    if not session_id:
        return
    with _cache_lock:
        _SESSION_CACHE.pop(session_id, None)
        _LAST_TOUCH.pop(session_id, None)


def fetch_session(session_id: str, *, force_remote: bool = False) -> dict | None:
    if not session_id:
        return None
    now = time.monotonic()
    if not force_remote:
        with _cache_lock:
            cached = _SESSION_CACHE.get(session_id)
        if cached and (now - cached[1]) < _CACHE_TTL:
            return dict(cached[0])
    record = select_one(TABLE, {"id": session_id})
    if record:
        _store_session_cache(session_id, record)
    else:
        _invalidate_session_cache(session_id)
    return record


def _touch_session_remote(session_id: str) -> None:
    try:
        patch_rows(TABLE, {"id": session_id}, {"last_seen_at": _iso(_utcnow())})
    except RuntimeError:
        pass


def touch_session(session_id: str) -> None:
    if not session_id:
        return
    now = time.monotonic()
    with _cache_lock:
        last_touch = _LAST_TOUCH.get(session_id, 0.0)
        if now - last_touch < _TOUCH_DEBOUNCE:
            cached = _SESSION_CACHE.get(session_id)
            if cached:
                record = dict(cached[0])
                record["last_seen_at"] = _iso(_utcnow())
                _SESSION_CACHE[session_id] = (record, now)
            return
        _LAST_TOUCH[session_id] = now
    threading.Thread(
        target=_touch_session_remote,
        args=(session_id,),
        name=f"session-touch-{session_id[:8]}",
        daemon=True,
    ).start()


def revoke_session(session_id: str) -> None:
    if not session_id:
        return
    _invalidate_session_cache(session_id)
    try:
        patch_rows(TABLE, {"id": session_id}, {"revoked_at": _iso(_utcnow())})
    except RuntimeError:
        pass


def delete_session(session_id: str) -> None:
    if not session_id:
        return
    _invalidate_session_cache(session_id)
    try:
        delete_rows(TABLE, {"id": session_id})
    except RuntimeError:
        pass


def is_session_active(record: dict | None) -> bool:
    if not record or record.get("revoked_at"):
        return False
    expires_raw = record.get("expires_at")
    if not expires_raw:
        return False
    try:
        expires = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    return expires > _utcnow()


def admin_from_record(record: dict) -> dict:
    return {
        "id": record.get("admin_id", ""),
        "email": record.get("admin_email", ""),
        "nome": record.get("admin_nome") or "Administrador",
        "perfil": record.get("admin_perfil") or "Administrador Master",
        "session_id": record.get("id", ""),
    }


def audit_login_event(*, email: str, success: bool, detail: str = "", origin: str = "master-web", metadata: dict | None = None):
    payload = {
        "email": str(email or ""),
        "success": bool(success),
        "detail": str(detail or "")[:500],
        "origin": origin,
        "metadata": metadata or {},
    }
    try:
        insert_row(AUDIT_TABLE, payload)
    except RuntimeError:
        pass
