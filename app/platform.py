"""Modelo de dados e colecoes inbound (leads, solicitacoes, event log)."""
from datetime import datetime

from .geography import coverage_metrics
from .platform_contract import (
    API_INBOUND_COMPANY_LEAD,
    API_INBOUND_DRIVER_APPLICATION,
    API_INBOUND_RESERVATION_REQUEST,
    API_PUBLIC_LOCATIONS_AGGREGATE,
    API_PUBLIC_STATISTICS,
    API_PUBLIC_VEHICLES,
    INBOUND_EVENT_COMPANY_LEAD,
    INBOUND_EVENT_DRIVER_APPLICATION,
    INBOUND_EVENT_RESERVATION_REQUEST,
)

ORIGIN_SITE = "Site"

COMPANY_LEAD_STATUSES = ["Novo", "Em contato", "Proposta enviada", "Convertido", "Perdido"]
DRIVER_LEAD_STATUSES = ["Novo", "Em analise", "Documentacao pendente", "Homologado", "Reprovado"]
TRANSPORT_REQUEST_STATUSES = ["Recebida", "Em analise", "Cotada", "Confirmada", "Cancelada"]

INTEGRATION_TYPES = ["Webhook", "API REST", "Importacao", "Exportacao"]
INTEGRATION_STATUSES = ["Ativa", "Inativa", "Configuracao", "Erro"]

EVENT_TYPES = {
    "site.company_lead.received": "Lead de empresa recebido",
    "site.driver_lead.received": "Lead de motorista recebido",
    "site.transport_request.received": "Solicitacao de transporte recebida",
    "company.created": "Empresa criada",
    "driver.created": "Motorista criado",
    "reservation.created": "Reserva criada",
    "integration.updated": "Integracao atualizada",
    "inbound.manual.created": "Registro criado no painel",
    "inbound.status.changed": "Status atualizado",
}

MAX_EVENT_LOG = 500

DEFAULT_INTEGRATIONS = [
    {
        "id": "int-0001",
        "nome": "Site publico - Leads de empresas",
        "tipo": "Webhook",
        "endpoint": API_INBOUND_COMPANY_LEAD,
        "status": "Configuracao",
        "ultima_sincronizacao": "",
        "observacoes": "Inbound oficial v1 — company.lead",
    },
    {
        "id": "int-0002",
        "nome": "Site publico - Leads de motoristas",
        "tipo": "Webhook",
        "endpoint": API_INBOUND_DRIVER_APPLICATION,
        "status": "Configuracao",
        "ultima_sincronizacao": "",
        "observacoes": "Inbound oficial v1 — driver.application",
    },
    {
        "id": "int-0003",
        "nome": "Site publico - Solicitacoes de transporte",
        "tipo": "Webhook",
        "endpoint": API_INBOUND_RESERVATION_REQUEST,
        "status": "Configuracao",
        "ultima_sincronizacao": "",
        "observacoes": "Inbound oficial v1 — reservation.request",
    },
    {
        "id": "int-0004",
        "nome": "Site publico - API publica",
        "tipo": "API REST",
        "endpoint": API_PUBLIC_STATISTICS,
        "status": "Configuracao",
        "ultima_sincronizacao": "",
        "observacoes": f"Cobertura, locations e vehicles via gateway v1 ({API_PUBLIC_LOCATIONS_AGGREGATE}, {API_PUBLIC_VEHICLES}).",
    },
]


def ensure_platform_collections(app):
    for key in ("company_leads", "driver_leads", "transport_requests", "event_log"):
        if not hasattr(app, key):
            setattr(app, key, [])
    app.company_leads = [normalize_company_lead(item) for item in app.company_leads]
    app.driver_leads = [normalize_driver_lead(item) for item in app.driver_leads]
    app.transport_requests = [normalize_transport_request(item) for item in app.transport_requests]
    app.event_log = [normalize_event(item) for item in app.event_log]


def _timestamp():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def next_record_id(prefix, records):
    numbers = []
    for item in records:
        record_id = str(item.get("id", ""))
        if record_id.startswith(f"{prefix}-"):
            try:
                numbers.append(int(record_id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"{prefix}-{max(numbers, default=0) + 1:04d}"


def normalize_company_lead(record):
    record = dict(record or {})
    status = record.get("status", "Novo")
    if status not in COMPANY_LEAD_STATUSES:
        status = "Novo"
    estado = str(record.get("estado_uf") or record.get("estado", "")).upper().strip()
    return {
        "id": record.get("id") or next_record_id("clead", []),
        "empresa": str(record.get("empresa", "")).strip(),
        "responsavel": str(record.get("responsavel", "")).strip(),
        "telefone": str(record.get("telefone", "")).strip(),
        "email": str(record.get("email", "")).strip(),
        "cidade": str(record.get("cidade", "")).strip(),
        "estado": estado,
        "estado_uf": estado,
        "origem": str(record.get("origem", ORIGIN_SITE)).strip() or ORIGIN_SITE,
        "status": status,
        "observacoes": str(record.get("observacoes", "")).strip(),
        "criado_em": record.get("criado_em") or _timestamp(),
        "atualizado_em": record.get("atualizado_em") or record.get("criado_em") or _timestamp(),
    }


def normalize_driver_lead(record):
    record = dict(record or {})
    status = record.get("status", "Novo")
    if status not in DRIVER_LEAD_STATUSES:
        status = "Novo"
    estado = str(record.get("estado_uf") or record.get("estado", "")).upper().strip()
    return {
        "id": record.get("id") or next_record_id("dlead", []),
        "nome": str(record.get("nome", "")).strip(),
        "telefone": str(record.get("telefone", "")).strip(),
        "whatsapp": str(record.get("whatsapp", "")).strip(),
        "email": str(record.get("email", "")).strip(),
        "cidade": str(record.get("cidade", "")).strip(),
        "estado": estado,
        "estado_uf": estado,
        "categoria": str(record.get("categoria", "")).strip(),
        "origem": str(record.get("origem", ORIGIN_SITE)).strip() or ORIGIN_SITE,
        "status": status,
        "observacoes": str(record.get("observacoes", "")).strip(),
        "criado_em": record.get("criado_em") or _timestamp(),
        "atualizado_em": record.get("atualizado_em") or record.get("criado_em") or _timestamp(),
    }


def normalize_transport_request(record):
    record = dict(record or {})
    status = record.get("status", "Recebida")
    if status not in TRANSPORT_REQUEST_STATUSES:
        status = "Recebida"
    origem = str(record.get("origem", "")).strip()
    destino = str(record.get("destino", "")).strip()
    if not origem and record.get("origem_manual"):
        origem = str(record.get("origem_manual", "")).strip()
    if not destino and record.get("destino_manual"):
        destino = str(record.get("destino_manual", "")).strip()
    return {
        "id": record.get("id") or next_record_id("treq", []),
        "origem": origem,
        "destino": destino,
        "data": str(record.get("data", "")).strip(),
        "hora": str(record.get("hora", "")).strip(),
        "empresa": str(record.get("empresa", "")).strip(),
        "nome": str(record.get("nome", "")).strip(),
        "telefone": str(record.get("telefone", "")).strip(),
        "email": str(record.get("email", "")).strip(),
        "origem_fonte": str(record.get("origem_fonte", ORIGIN_SITE)).strip() or ORIGIN_SITE,
        "origem_modo": str(record.get("origem_modo", "")).strip(),
        "destino_modo": str(record.get("destino_modo", "")).strip(),
        "status": status,
        "observacoes": str(record.get("observacoes", "")).strip(),
        "criado_em": record.get("criado_em") or _timestamp(),
        "atualizado_em": record.get("atualizado_em") or record.get("criado_em") or _timestamp(),
    }


def normalize_event(record):
    record = dict(record or {})
    event_type = str(record.get("tipo", "")).strip()
    return {
        "id": record.get("id") or next_record_id("evt", []),
        "tipo": event_type,
        "titulo": str(record.get("titulo") or EVENT_TYPES.get(event_type, event_type)).strip(),
        "resumo": str(record.get("resumo", "")).strip(),
        "origem": str(record.get("origem", "painel")).strip() or "painel",
        "referencia_id": str(record.get("referencia_id", "")).strip(),
        "payload": dict(record.get("payload") or {}),
        "criado_em": record.get("criado_em") or _timestamp(),
    }


def log_event(app, event_type, resumo, referencia_id="", origem="painel", payload=None, titulo=""):
    ensure_platform_collections(app)
    event = normalize_event(
        {
            "tipo": event_type,
            "titulo": titulo or EVENT_TYPES.get(event_type, event_type),
            "resumo": resumo,
            "origem": origem,
            "referencia_id": referencia_id,
            "payload": payload or {},
        }
    )
    app.event_log.insert(0, event)
    app.event_log = app.event_log[:MAX_EVENT_LOG]
    return event


def count_by_status(records, status):
    return sum(1 for item in records if item.get("status") == status)


def company_display_name(client):
    return client.get("razao_social") or client.get("nome_fantasia") or client.get("nome", "")


def is_corporate_client(client):
    return client.get("tipo_pessoa") == "juridica" or bool(client.get("cnpj") or client.get("razao_social"))


def build_executive_stats(app):
    ensure_platform_collections(app)
    clients = list(getattr(app, "clients", []))
    drivers = list(getattr(app, "drivers", []))
    reservations = list(getattr(app, "reservations", []))
    points = list(getattr(app, "operational_points", []))
    geo = coverage_metrics(points)

    corporate_clients = [client for client in clients if is_corporate_client(client)]
    active_corporate = [
        client
        for client in corporate_clients
        if str(client.get("status_empresa", client.get("status", "Ativa"))).lower() not in {"inativa", "bloqueada", "bloqueado"}
    ]
    homologated_drivers = [
        driver
        for driver in drivers
        if str(driver.get("status_operacional", driver.get("frota", ""))).lower() in {"ativo", "homologado", "operando"}
    ]

    return {
        "empresas_cadastradas": len(corporate_clients),
        "empresas_ativas": len(active_corporate) or len(corporate_clients),
        "motoristas_homologados": len(homologated_drivers) or len(drivers),
        "estados_cobertos": geo["states_with_points"],
        "cidades_cobertas": geo["cities_with_points"],
        "pontos_operacionais": geo["total_points"],
        "leads_empresas": len(app.company_leads),
        "leads_motoristas": len(app.driver_leads),
        "leads_novos": count_by_status(app.company_leads, "Novo") + count_by_status(app.driver_leads, "Novo"),
        "solicitacoes_recebidas": len(app.transport_requests),
        "solicitacoes_pendentes": count_by_status(app.transport_requests, "Recebida") + count_by_status(app.transport_requests, "Em analise"),
        "reservas_total": len(reservations),
        "eventos_total": len(app.event_log),
    }


INBOUND_NORMALIZERS = {
    INBOUND_EVENT_COMPANY_LEAD: normalize_company_lead,
    INBOUND_EVENT_DRIVER_APPLICATION: normalize_driver_lead,
    INBOUND_EVENT_RESERVATION_REQUEST: normalize_transport_request,
}

INBOUND_COLLECTIONS = {
    INBOUND_EVENT_COMPANY_LEAD: "company_leads",
    INBOUND_EVENT_DRIVER_APPLICATION: "driver_leads",
    INBOUND_EVENT_RESERVATION_REQUEST: "transport_requests",
}

INBOUND_RECEIVED_EVENTS = {
    INBOUND_EVENT_COMPANY_LEAD: "site.company_lead.received",
    INBOUND_EVENT_DRIVER_APPLICATION: "site.driver_lead.received",
    INBOUND_EVENT_RESERVATION_REQUEST: "site.transport_request.received",
}
