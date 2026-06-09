"""Autenticacao administrativa web com sessoes persistidas."""
from __future__ import annotations

import secrets

from app.admin_auth import authenticate_admin

from ..config import get_settings
from ..repositories.session_repository import (
    admin_from_record,
    audit_login_event,
    create_session_record,
    delete_session,
    fetch_session,
    is_session_active,
    revoke_session,
    touch_session,
)


def login_admin(email, password):
    return authenticate_admin(email, password)


def create_web_session(request, admin: dict) -> str:
    settings = get_settings()
    session_id = secrets.token_urlsafe(32)
    create_session_record(
        session_id=session_id,
        admin=admin,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        max_age_seconds=settings.session_max_age,
    )
    request.session.clear()
    request.session["sid"] = session_id
    audit_login_event(
        email=admin.get("email", ""),
        success=True,
        detail="login web",
        metadata={"session_id": session_id, "ip": _client_ip(request)},
    )
    return session_id


def resolve_admin(request):
    session_id = str(request.session.get("sid", "") or "").strip()
    if not session_id:
        return None
    record = fetch_session(session_id)
    if not is_session_active(record):
        request.session.clear()
        if record:
            revoke_session(session_id)
        return None
    touch_session(session_id)
    return admin_from_record(record)


def logout_admin(request):
    session_id = str(request.session.get("sid", "") or "").strip()
    record = fetch_session(session_id) if session_id else None
    admin = admin_from_record(record) if is_session_active(record) else None
    if session_id:
        revoke_session(session_id)
        delete_session(session_id)
    request.session.clear()
    if admin:
        audit_login_event(
            email=admin.get("email", ""),
            success=True,
            detail="logout web",
            metadata={"session_id": session_id, "ip": _client_ip(request)},
        )


def _client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or ""
    return ""
