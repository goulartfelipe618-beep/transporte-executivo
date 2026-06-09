"""Persistencia de sessoes administrativas — Supabase REST + SQLAlchemy async opcional."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.repository.supabase_client import delete_rows, insert_row, patch_rows, select_one

TABLE = "master_admin_sessions"
AUDIT_TABLE = "master_login_audit"


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
    return row or payload


def fetch_session(session_id: str) -> dict | None:
    if not session_id:
        return None
    return select_one(TABLE, {"id": session_id})


def touch_session(session_id: str) -> None:
    patch_rows(TABLE, {"id": session_id}, {"last_seen_at": _iso(_utcnow())})


def revoke_session(session_id: str) -> None:
    if not session_id:
        return
    patch_rows(TABLE, {"id": session_id}, {"revoked_at": _iso(_utcnow())})


def delete_session(session_id: str) -> None:
    if not session_id:
        return
    delete_rows(TABLE, {"id": session_id})


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
