"""CRUD de usuarios corporativos — persistencia em company_users + sync runtime."""
from __future__ import annotations

import secrets
import string

from app.company_model import find_company_user, normalize_company_user
from app.company_portal_services import delete_user, save_user, user_dto
from app.portal_auth import USER_TYPE_COMPANY, prepare_password_field

from ..validators.company import map_service_error

_TEMP_CHARS = string.ascii_letters + string.digits


def generate_temporary_password(length=12):
    return "".join(secrets.choice(_TEMP_CHARS) for _ in range(length))


def _find_company(app, company_id):
    company_id = str(company_id or "")
    for client in getattr(app, "clients", []) or []:
        if str(client.get("id", "")) == company_id:
            return client
    return None


def _company_uuid(company):
    return str(company.get("uuid") or "")


def _sync_runtime_users(company, users):
    company["usuarios"] = list(users or [])


def _migrate_embedded_users(app, company):
    from app.repository import supabase_client as db
    from app.repository.supabase_store import load_company_users, upsert_company_user

    if not db.is_configured():
        return
    company_uuid = _company_uuid(company)
    if not company_uuid:
        return
    existing = load_company_users(company_uuid)
    if existing:
        _sync_runtime_users(company, existing)
        return
    embedded = list(company.get("usuarios") or [])
    if not embedded:
        return
    saved_users = []
    for row in embedded:
        item = dict(row)
        if item.get("senha"):
            item["password_hash"] = prepare_password_field(item["senha"])
        saved = upsert_company_user(
            item,
            company_uuid=company_uuid,
            company_legacy_id=company.get("id"),
        )
        if saved:
            item["uuid"] = saved.get("id")
        saved_users.append(item)
    _sync_runtime_users(company, saved_users)
    if hasattr(app, "save_state"):
        app.save_state()


def list_users(app, company_id):
    company = _find_company(app, company_id)
    if not company:
        return []
    _migrate_embedded_users(app, company)
    return [user_dto(u) for u in company.get("usuarios") or []]


def find_user(app, company_id, user_id):
    company = _find_company(app, company_id)
    if not company:
        return None
    _migrate_embedded_users(app, company)
    for user in company.get("usuarios") or []:
        if str(user.get("id", "")) == str(user_id):
            return user_dto(user)
    return None


def _persist_user(app, company, user_record):
    from app.repository import supabase_client as db
    from app.repository.supabase_store import upsert_company_user

    company_uuid = _company_uuid(company)
    if not company_uuid:
        if hasattr(app, "save_state"):
            app.save_state()
        return user_record
    payload = dict(user_record)
    payload["password_hash"] = prepare_password_field(payload.get("senha", ""))
    saved = upsert_company_user(
        payload,
        company_uuid=company_uuid,
        company_legacy_id=company.get("id"),
    )
    if saved and saved.get("id"):
        user_record["uuid"] = saved["id"]
    _sync_runtime_users(company, company.get("usuarios") or [])
    if hasattr(app, "save_state"):
        app.save_state()
    return user_record


def create_user(app, company_id, form_data, *, actor=None, temporary_password=None, must_change_password=True):
    company = _find_company(app, company_id)
    if not company:
        raise ValueError("empresa_nao_encontrada")
    _migrate_embedded_users(app, company)
    temp_password = temporary_password or str(form_data.get("senha", "")).strip() or generate_temporary_password()
    payload = {
        "nome": form_data.get("nome", ""),
        "email": form_data.get("email", ""),
        "telefone": form_data.get("telefone", ""),
        "perfil": form_data.get("perfil", "Solicitante"),
        "status": form_data.get("status", "Ativo"),
        "senha": temp_password,
        "must_change_password": bool(must_change_password),
    }
    actor = actor or {"id": "master-admin", "nome": "Admin Master"}
    try:
        saved = save_user(company, payload, actor=actor)
    except ValueError as exc:
        raise ValueError(map_service_error(exc.args[0] if exc.args else exc)) from exc
    for row in company.get("usuarios") or []:
        if str(row.get("email", "")).lower() == str(payload.get("email", "")).lower():
            row["must_change_password"] = bool(must_change_password)
            row["senha"] = temp_password
            _persist_user(app, company, row)
            break
    return saved, temp_password if must_change_password else ""


def update_user(app, company_id, user_id, form_data, *, actor=None):
    company = _find_company(app, company_id)
    if not company:
        raise ValueError("empresa_nao_encontrada")
    _migrate_embedded_users(app, company)
    payload = {
        "id": user_id,
        "nome": form_data.get("nome", ""),
        "email": form_data.get("email", ""),
        "telefone": form_data.get("telefone", ""),
        "perfil": form_data.get("perfil", "Solicitante"),
        "status": form_data.get("status", "Ativo"),
    }
    senha = str(form_data.get("senha", "")).strip()
    if senha:
        payload["senha"] = senha
        payload["must_change_password"] = form_data.get("must_change_password") in {"1", "true", "on", True}
    actor = actor or {"id": "master-admin", "nome": "Admin Master"}
    try:
        saved = save_user(company, payload, actor=actor)
    except ValueError as exc:
        raise ValueError(map_service_error(exc.args[0] if exc.args else exc)) from exc
    for row in company.get("usuarios") or []:
        if str(row.get("id", "")) == str(user_id):
            if senha:
                row["must_change_password"] = payload.get("must_change_password", False)
            _persist_user(app, company, row)
            break
    return saved


def deactivate_user(app, company_id, user_id, *, actor=None):
    company = _find_company(app, company_id)
    if not company:
        raise ValueError("empresa_nao_encontrada")
    _migrate_embedded_users(app, company)
    actor = actor or {"id": "master-admin", "nome": "Admin Master"}
    try:
        delete_user(company, user_id, actor=actor)
    except ValueError as exc:
        raise ValueError(map_service_error(exc.args[0] if exc.args else exc)) from exc
    from app.repository import supabase_client as db
    from app.repository.supabase_store import delete_company_user_row

    if db.is_configured():
        delete_company_user_row(
            company_uuid=_company_uuid(company),
            legacy_user_id=user_id,
            company_legacy_id=company.get("id"),
        )
    if hasattr(app, "save_state"):
        app.save_state()
    return True


def provision_auto_admin(app, company, *, temporary_password=None):
    if not company:
        return None, ""
    email = str(company.get("email", "")).strip().lower()
    if not email:
        return None, ""
    _migrate_embedded_users(app, company)
    existing = find_company_user(company, email)
    temp_password = temporary_password or generate_temporary_password()
    if existing:
        if existing.get("must_change_password"):
            return user_dto(existing), ""
        existing["senha"] = temp_password
        existing["must_change_password"] = True
        existing["perfil"] = existing.get("perfil") or "Administrador da Empresa"
        existing["status"] = existing.get("status") or "Ativo"
        _persist_user(app, company, existing)
        return user_dto(existing), temp_password
    payload = normalize_company_user(
        {
            "nome": company.get("responsavel") or company.get("razao_social") or "Administrador",
            "email": email,
            "telefone": company.get("telefone", ""),
            "perfil": "Administrador da Empresa",
            "status": "Ativo",
            "senha": temp_password,
            "must_change_password": True,
        },
        company.get("id", ""),
    )
    company.setdefault("usuarios", []).append(payload)
    _persist_user(app, company, payload)
    return user_dto(payload), temp_password


def portal_last_access(app, company):
    from app.company_model import company_key

    company_id = str(company.get("id", ""))
    slug = company_key(company)
    user_ids = {str(u.get("id", "")) for u in company.get("usuarios") or []}
    latest = ""
    for session in getattr(app, "portal_sessions", []) or []:
        if session.get("user_type") != USER_TYPE_COMPANY:
            continue
        tenant = str(session.get("tenant_id", ""))
        session_slug = str(session.get("slug", ""))
        if tenant and tenant != company_id and session_slug != slug:
            continue
        if str(session.get("user_id", "")) not in user_ids:
            continue
        stamp = str(session.get("last_activity") or session.get("created_at") or "")
        if stamp and (not latest or stamp > latest):
            latest = stamp
    activity = (company.get("portal_activity") or [{}])[0].get("criado_em", "")
    if activity and (not latest or activity > latest):
        latest = activity
    return latest
