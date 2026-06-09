"""CRUD de leads de empresas — logica extraida de inbound_ui.py (sem Tkinter)."""
from __future__ import annotations

from datetime import datetime

from app.platform import (
    COMPANY_LEAD_STATUSES,
    ORIGIN_SITE,
    ensure_platform_collections,
    log_event,
    next_record_id,
    normalize_company_lead,
)

BLOCK_STATUS = "Perdido"
ACTIVE_STATUS = "Novo"
OPEN_STATUSES = {"Novo", "Em contato"}


def lead_display_name(item):
    return str(item.get("empresa", "")).strip() or str(item.get("id", ""))


def list_company_leads(app, *, search="", status="", include_blocked=True):
    ensure_platform_collections(app)
    items = []
    query = str(search or "").strip().lower()
    status_filter = str(status or "").strip()
    for item in getattr(app, "company_leads", []) or []:
        item_status = str(item.get("status", "")).strip()
        if not include_blocked and item_status == BLOCK_STATUS:
            continue
        if status_filter and item_status != status_filter:
            continue
        if query:
            haystack = " ".join(
                [
                    item.get("id", ""),
                    item.get("empresa", ""),
                    item.get("responsavel", ""),
                    item.get("telefone", ""),
                    item.get("email", ""),
                    item.get("cidade", ""),
                    item.get("estado", ""),
                    item.get("status", ""),
                    item.get("origem", ""),
                ]
            ).lower()
            if query not in haystack:
                continue
        items.append(item)
    items.sort(key=lambda row: str(row.get("criado_em", "")), reverse=True)
    return items


def find_company_lead_by_id(app, lead_id):
    lead_id = str(lead_id or "")
    for item in getattr(app, "company_leads", []) or []:
        if str(item.get("id", "")) == lead_id:
            return item
    return None


def _build_payload(form_data, *, existing=None):
    existing = existing or {}
    merged = dict(existing)
    for key in (
        "empresa",
        "responsavel",
        "telefone",
        "email",
        "cidade",
        "estado",
        "origem",
        "status",
        "observacoes",
    ):
        if key in form_data:
            merged[key] = str(form_data.get(key, "")).strip()
    merged["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    return normalize_company_lead(merged)


def create_company_lead(app, form_data):
    ensure_platform_collections(app)
    records = getattr(app, "company_leads", []) or []
    payload = _build_payload(form_data)
    payload["id"] = next_record_id("clead", records)
    payload["criado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    if not payload.get("origem"):
        payload["origem"] = ORIGIN_SITE
    records.insert(0, payload)
    app.company_leads = records
    event = (
        "site.company_lead.received"
        if payload.get("origem") == ORIGIN_SITE
        else "inbound.manual.created"
    )
    log_event(
        app,
        event,
        f'Lead de empresa criado: {payload.get("id", "")}',
        referencia_id=payload.get("id", ""),
        origem=payload.get("origem", "painel"),
    )
    if hasattr(app, "save_state"):
        app.save_state()
    return payload


def update_company_lead(app, lead_id, form_data):
    item = find_company_lead_by_id(app, lead_id)
    if not item:
        raise ValueError("lead_empresa_nao_encontrado")
    old_status = item.get("status")
    payload = _build_payload(form_data, existing=item)
    item.update(payload)
    if old_status != item.get("status"):
        log_event(
            app,
            "inbound.status.changed",
            f'Status alterado para {item.get("status")}',
            referencia_id=item.get("id", ""),
        )
    if hasattr(app, "save_state"):
        app.save_state()
    return item


def block_company_lead(app, lead_id):
    item = find_company_lead_by_id(app, lead_id)
    if not item:
        raise ValueError("lead_empresa_nao_encontrado")
    item["status"] = BLOCK_STATUS
    item["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    log_event(
        app,
        "inbound.status.changed",
        f"Lead marcado como {BLOCK_STATUS}",
        referencia_id=item.get("id", ""),
    )
    if hasattr(app, "save_state"):
        app.save_state()
    return item


def activate_company_lead(app, lead_id):
    item = find_company_lead_by_id(app, lead_id)
    if not item:
        raise ValueError("lead_empresa_nao_encontrado")
    item["status"] = ACTIVE_STATUS
    item["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    log_event(
        app,
        "inbound.status.changed",
        f"Status alterado para {ACTIVE_STATUS}",
        referencia_id=item.get("id", ""),
    )
    if hasattr(app, "save_state"):
        app.save_state()
    return item


def linked_company(app, item):
    empresa = str(item.get("empresa", "")).strip().lower()
    if not empresa:
        return None
    for client in getattr(app, "clients", []) or []:
        names = [
            str(client.get("razao_social", "")).lower(),
            str(client.get("nome_fantasia", "")).lower(),
            str(client.get("nome", "")).lower(),
            str(client.get("empresa", "")).lower(),
        ]
        if empresa in names:
            return client
    return None


def lead_stats(app, item):
    return {
        "status": item.get("status", ""),
        "origem": item.get("origem", ""),
        "tem_empresa": bool(linked_company(app, item)),
        "bloqueado": str(item.get("status", "")) == BLOCK_STATUS,
    }


def list_summary(app):
    ensure_platform_collections(app)
    records = getattr(app, "company_leads", []) or []
    abertos = sum(1 for item in records if item.get("status") in OPEN_STATUSES)
    convertidos = sum(1 for item in records if item.get("status") == "Convertido")
    perdidos = sum(1 for item in records if item.get("status") == BLOCK_STATUS)
    from_site = sum(1 for item in records if str(item.get("origem", "")).strip() == ORIGIN_SITE)
    return {
        "total": len(records),
        "abertos": abertos,
        "convertidos": convertidos,
        "perdidos": perdidos,
        "origem_site": from_site,
    }


def filter_options():
    return {"statuses": COMPANY_LEAD_STATUSES}
