"""CRUD de empresas corporativas — logica extraida de full_features.py (sem Tkinter)."""
from __future__ import annotations

from app.company_model import (
    COMPANY_STATUSES,
    company_reservations,
    company_transport_requests,
    ensure_company_portal_structure,
    is_corporate_client,
)
from app.portal_urls import company_portal_base, company_portal_link

from .company_user_service import portal_last_access, provision_auto_admin

DONE_STATUSES = {"concluida", "concluído", "concluido", "finalizada"}
CANCEL_STATUSES = {"cancelada", "cancelado", "rejeitada"}


def company_display_name(company):
    return company.get("nome_fantasia") or company.get("razao_social") or company.get("nome", "")


def company_document(company):
    return company.get("cnpj") or company.get("cpf") or company.get("documento", "")


def _parse_money(value):
    raw = str(value or "").replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.0


def list_corporate_companies(app, *, search="", include_blocked=True):
    items = []
    query = str(search or "").strip().lower()
    for client in getattr(app, "clients", []) or []:
        if not is_corporate_client(client):
            continue
        if not include_blocked and client.get("status_empresa") == "Bloqueada":
            continue
        if query:
            haystack = " ".join(
                [
                    company_display_name(client),
                    company_document(client),
                    str(client.get("telefone", "")),
                    str(client.get("email", "")),
                    str(client.get("id", "")),
                ]
            ).lower()
            if query not in haystack:
                continue
        items.append(client)
    items.sort(key=lambda row: company_display_name(row).lower())
    return items


def find_company_by_id(app, company_id):
    company_id = str(company_id or "")
    for client in getattr(app, "clients", []) or []:
        if str(client.get("id", "")) == company_id and is_corporate_client(client):
            return client
    return None


def _collect_addresses(form_data):
    enderecos = []
    main_endereco = str(form_data.get("endereco", "")).strip()
    main_tipo = str(form_data.get("endereco_tipo", "casa")).strip() or "casa"
    if main_endereco:
        enderecos.append({"tipo": main_tipo, "endereco": main_endereco})
    extra = str(form_data.get("endereco_extra", "")).strip()
    if extra:
        enderecos.append({"tipo": "outro", "endereco": extra})
    return enderecos


def _build_company_payload(form_data, *, existing=None):
    existing = existing or {}
    payload = dict(existing)
    fields = [
        "razao_social",
        "nome_fantasia",
        "cnpj",
        "inscricao_estadual",
        "email",
        "telefone",
        "telefone_2",
        "responsavel",
        "estado",
        "cidade",
        "status_empresa",
    ]
    for key in fields:
        if key in form_data:
            payload[key] = str(form_data.get(key, "")).strip()
    payload["tipo_pessoa"] = "juridica"
    payload["nome"] = payload.get("nome_fantasia") or payload.get("razao_social") or payload.get("nome", "")
    portal_ativo = form_data.get("portal_ativo")
    if portal_ativo is not None:
        payload["portal_ativo"] = portal_ativo in {"1", "true", "on", True, "Ativo", "ativo"}
    enderecos = _collect_addresses(form_data)
    if enderecos:
        payload["endereco"] = enderecos[0]["endereco"]
        payload["endereco_tipo"] = enderecos[0]["tipo"]
        payload["enderecos"] = enderecos
    if payload.get("status_empresa") not in COMPANY_STATUSES:
        payload["status_empresa"] = existing.get("status_empresa") or "Ativa"
    return payload


def create_company(app, form_data):
    clients = getattr(app, "clients", []) or []
    payload = _build_company_payload(form_data)
    payload = ensure_company_portal_structure(payload, company_portal_base(), clients)
    clients.append(payload)
    app.clients = clients
    admin_user, temp_password = provision_auto_admin(app, payload)
    if hasattr(app, "save_state"):
        app.save_state()
    return payload, admin_user, temp_password


def update_company(app, company_id, form_data):
    company = find_company_by_id(app, company_id)
    if not company:
        raise ValueError("empresa_nao_encontrada")
    payload = _build_company_payload(form_data, existing=company)
    payload = ensure_company_portal_structure(payload, company_portal_base(), getattr(app, "clients", []) or [])
    company.update(payload)
    admin_user, temp_password = provision_auto_admin(app, company)
    if hasattr(app, "save_state"):
        app.save_state()
    return company, admin_user, temp_password


def block_company(app, company_id):
    company = find_company_by_id(app, company_id)
    if not company:
        raise ValueError("empresa_nao_encontrada")
    company["status_empresa"] = "Bloqueada"
    company["portal_ativo"] = False
    if hasattr(app, "save_state"):
        app.save_state()
    return company


def get_portal_link(company):
    return company_portal_link(company)


def portal_info(company):
    from app.company_model import company_key

    return {
        "portal_ativo": bool(company.get("portal_ativo", True)),
        "portal_key": company_key(company),
        "portal_codigo": str(company.get("portal_codigo", "")),
        "portal_link": get_portal_link(company),
        "portal_criado_em": company.get("portal_criado_em", ""),
        "status_empresa": company.get("status_empresa", "Ativa"),
    }


def company_stats(app, company):
    reservations = company_reservations(app, company)
    requests = company_transport_requests(app, company)
    total = len(reservations)
    done = 0
    cancelled = 0
    revenue = 0.0
    last_activity = ""
    for item in reservations:
        status = str(item.get("status", "")).strip().lower().replace("í", "i")
        if status in DONE_STATUSES:
            done += 1
            revenue += _parse_money(item.get("valor"))
        if status in CANCEL_STATUSES:
            cancelled += 1
        stamp = str(item.get("atualizado_em") or item.get("data") or item.get("criado_em") or "")
        if stamp and (not last_activity or stamp > last_activity):
            last_activity = stamp
    for item in requests:
        stamp = str(item.get("atualizado_em") or item.get("criado_em") or item.get("data") or "")
        if stamp and (not last_activity or stamp > last_activity):
            last_activity = stamp
    portal_access = portal_last_access(app, company)
    if portal_access and (not last_activity or portal_access > last_activity):
        last_activity = portal_access
    activity_log = (company.get("portal_activity") or [{}])[0].get("criado_em", "")
    if activity_log and (not last_activity or activity_log > last_activity):
        last_activity = activity_log
    return {
        "total_reservas": total,
        "reservas_concluidas": done,
        "reservas_canceladas": cancelled,
        "receita_total": revenue,
        "receita_total_fmt": f"R$ {revenue:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "solicitacoes": len(requests),
        "ultima_atividade": last_activity or "—",
    }


def list_summary(app):
    companies = list_corporate_companies(app, include_blocked=True)
    active = sum(1 for item in companies if item.get("status_empresa") == "Ativa")
    blocked = sum(1 for item in companies if item.get("status_empresa") == "Bloqueada")
    return {"total": len(companies), "ativas": active, "bloqueadas": blocked}
