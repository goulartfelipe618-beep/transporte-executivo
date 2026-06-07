"""Mapeamento JSON local <-> linhas Supabase (legacy_admin_id + dados_extra)."""
from __future__ import annotations

import re
from copy import deepcopy

COLLECTION_TABLE = {
    "reservations": "reservations",
    "drivers": "drivers",
    "vehicles": "vehicles",
    "operational_points": "operational_points",
    "partner_networks": "partner_networks",
    "network_contributors": "network_contributors",
    "network_commissions": "network_commissions",
    "contributor_commissions": "contributor_commissions",
    "network_access_logs": "network_access_logs",
    "audit_log": "audit_log",
    "transport_requests": "transport_requests",
    "company_leads": "company_leads",
    "driver_leads": "driver_leads",
    "event_log": "event_log",
    "portal_sessions": "portal_sessions",
}

KNOWN_COLUMNS = {
    "reservations": {
        "legacy_admin_id", "numero", "cliente", "empresa", "trajeto", "origem", "destino", "data", "hora",
        "status", "valor", "tipo", "observacoes", "motorista", "partner_slug", "partner_code", "contributor_code",
        "source", "flow", "canal_origem", "via_qr", "transport_request_legacy_id", "partner_id", "contributor_id",
        "company_id", "driver_id", "cost_center_id", "dados_extra",
    },
    "drivers": {
        "legacy_admin_id", "portal_slug", "nome", "cpf", "rg", "email", "telefone", "estado", "cidade", "frota",
        "validade_cnh", "portal_ativo", "password_hash", "activation_token", "portal_link", "dados_extra",
    },
    "vehicles": {
        "legacy_admin_id", "placa", "tipo_veiculo", "marca", "modelo", "ano", "cor", "capacidade", "bagagens",
        "aplicacao", "status", "portal_publicado", "veiculo_de_rede", "dados_extra",
    },
    "operational_points": {
        "legacy_admin_id", "nome", "tipo", "estado_uf", "cidade_nome", "endereco", "website_slug", "website_path",
        "status", "portal_publicado", "dados_extra",
    },
    "partner_networks": {
        "legacy_admin_id", "slug", "codigo", "portal_key", "nome_rede", "razao_social", "tipo_rede",
        "responsavel_nome", "email", "telefone", "whatsapp", "cidade", "estado", "logo_url", "banner_url",
        "primary_color", "secondary_color", "texto_boas_vindas", "comissao_percentual", "booking_token",
        "link_publico", "portal_ativo", "status", "observacoes", "dados_extra",
    },
    "network_contributors": {
        "legacy_admin_id", "partner_id", "codigo_ref", "nome", "email", "telefone", "whatsapp", "cargo",
        "percentual_comissao", "link_contribuidor", "ativo", "status", "dados_extra",
    },
    "network_commissions": {
        "legacy_admin_id", "partner_id", "reservation_id", "reservation_numero", "transport_request_id",
        "valor_base", "percentual", "valor_bruto", "valor_comissao", "status_pagamento", "dados_extra",
    },
    "contributor_commissions": {
        "legacy_admin_id", "partner_id", "contributor_id", "reservation_id", "reservation_numero", "percentual",
        "valor_comissao", "status_pagamento", "dados_extra",
    },
    "network_access_logs": {
        "legacy_admin_id", "partner_id", "contributor_id", "canal", "ref", "ip_address", "user_agent", "metadata",
    },
    "audit_log": {
        "legacy_admin_id", "action", "actor_type", "actor_id", "partner_id", "company_id", "driver_id",
        "reservation_id", "record_table", "record_id", "payload", "ip_address",
    },
    "transport_requests": {
        "legacy_admin_id", "origem", "destino", "data", "hora", "passageiros", "categoria", "status",
        "approval_status", "origem_fonte", "observacoes", "partner_slug", "partner_code", "contributor_code",
        "source", "flow", "canal_origem", "via_qr", "nome", "telefone", "email", "valor_estimado",
        "company_id", "cost_center_id", "company_user_id", "reservation_id", "partner_id", "contributor_id",
        "dados_extra",
    },
    "company_leads": {
        "legacy_admin_id", "empresa", "responsavel", "telefone", "email", "cidade", "estado", "estado_uf",
        "origem", "status", "observacoes", "dados_extra",
    },
    "driver_leads": {
        "legacy_admin_id", "nome", "telefone", "email", "cidade", "estado", "estado_uf", "origem", "status",
        "observacoes", "dados_extra",
    },
    "event_log": {
        "legacy_admin_id", "tipo", "titulo", "resumo", "origem", "referencia_id", "user_type", "user_id", "payload",
    },
    "portal_sessions": {
        "session_token", "user_type", "driver_id", "company_user_id", "legacy_user_admin_id", "slug",
        "expires_at", "last_activity", "partner_id", "partner_portal_user_id", "dados_extra",
    },
}


def parse_money(value):
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value or "0").replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return 0.0


def _extra(item, known):
    extra = {}
    for key, value in item.items():
        if key not in known and key not in {"id", "uuid"}:
            extra[key] = value
    return extra


def _merge_row(row):
    item = deepcopy(row.get("dados_extra") or {})
    db_id = row.get("id")
    legacy = row.get("legacy_admin_id") or row.get("session_token") or ""
    if legacy:
        item["id"] = legacy
    if db_id:
        item["uuid"] = db_id
    for key, value in row.items():
        if key in {"id", "dados_extra", "created_at", "updated_at"}:
            continue
        if key == "legacy_admin_id":
            continue
        if key == "primary_color":
            item.setdefault("cor_primaria", value)
        elif key == "secondary_color":
            item.setdefault("cor_secundaria", value)
        elif key == "nome_rede" and "nome" not in item:
            item["nome"] = value
        elif key == "tipo_veiculo" and "tipo" not in item:
            item["tipo"] = value
        elif key == "valor" and "valor" not in item:
            item["valor"] = f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            item.setdefault(key, value)
    return item


class RefResolver:
    def __init__(self):
        self._legacy_to_uuid = {}

    def register(self, legacy_id, uuid):
        if legacy_id and uuid:
            self._legacy_to_uuid[str(legacy_id)] = str(uuid)

    def uuid(self, legacy_id):
        if not legacy_id:
            return None
        key = str(legacy_id)
        resolved = self._legacy_to_uuid.get(key)
        if resolved:
            return resolved
        if len(key) == 36 and key.count("-") == 4:
            return key
        return None


def to_partner_network_row(item, resolver: RefResolver):
    known = KNOWN_COLUMNS["partner_networks"]
    row = {
        "legacy_admin_id": item.get("id"),
        "slug": item.get("slug"),
        "codigo": item.get("codigo") or item.get("codigo_acesso"),
        "portal_key": item.get("portal_key"),
        "nome_rede": item.get("nome_rede") or item.get("nome"),
        "razao_social": item.get("razao_social"),
        "tipo_rede": item.get("tipo_rede", "AFILIADO"),
        "responsavel_nome": item.get("responsavel_nome") or item.get("responsavel"),
        "email": item.get("email"),
        "telefone": item.get("telefone"),
        "whatsapp": item.get("whatsapp"),
        "cidade": item.get("cidade"),
        "estado": item.get("estado"),
        "logo_url": item.get("logo_url"),
        "banner_url": item.get("banner_url"),
        "primary_color": item.get("cor_primaria") or item.get("primary_color"),
        "secondary_color": item.get("cor_secundaria") or item.get("secondary_color"),
        "texto_boas_vindas": item.get("texto_boas_vindas"),
        "comissao_percentual": float(item.get("comissao_percentual", item.get("comissao_rede", item.get("comissao_pct", 0))) or 0),
        "booking_token": item.get("booking_token"),
        "link_publico": item.get("link_publico") or item.get("booking_link"),
        "portal_ativo": bool(item.get("portal_ativo", item.get("ativo", True))),
        "status": item.get("status", "Ativo"),
        "observacoes": item.get("observacoes"),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_network_contributor_row(item, resolver: RefResolver):
    known = KNOWN_COLUMNS["network_contributors"]
    partner_uuid = resolver.uuid(item.get("partner_id"))
    row = {
        "legacy_admin_id": item.get("id"),
        "partner_id": partner_uuid,
        "codigo_ref": item.get("codigo_ref"),
        "nome": item.get("nome"),
        "email": item.get("email"),
        "telefone": item.get("telefone"),
        "whatsapp": item.get("whatsapp"),
        "cargo": item.get("cargo"),
        "percentual_comissao": float(item.get("percentual_comissao", 0) or 0),
        "link_contribuidor": item.get("link_contribuidor"),
        "ativo": bool(item.get("ativo", True)),
        "status": item.get("status", "Ativo"),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None and v != ""}


def to_driver_row(item):
    known = KNOWN_COLUMNS["drivers"]
    row = {
        "legacy_admin_id": item.get("id"),
        "portal_slug": item.get("portal_slug") or item.get("slug"),
        "nome": item.get("nome"),
        "cpf": item.get("cpf"),
        "rg": item.get("rg"),
        "email": item.get("email"),
        "telefone": item.get("telefone"),
        "estado": item.get("estado") or (item.get("cidade", "").split("/")[-1].strip() if "/" in str(item.get("cidade", "")) else ""),
        "cidade": item.get("cidade"),
        "frota": item.get("frota"),
        "validade_cnh": item.get("validade_cnh"),
        "portal_ativo": bool(item.get("portal_ativo", "portal" in str(item.get("portal", "")).lower())),
        "password_hash": item.get("password_hash"),
        "activation_token": item.get("activation_token"),
        "portal_link": item.get("link") or item.get("portal_link"),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_vehicle_row(item):
    known = KNOWN_COLUMNS["vehicles"]
    row = {
        "legacy_admin_id": item.get("id"),
        "placa": item.get("placa"),
        "tipo_veiculo": item.get("tipo_veiculo") or item.get("tipo") or item.get("categoria"),
        "marca": item.get("marca"),
        "modelo": item.get("modelo"),
        "ano": int(item["ano"]) if str(item.get("ano", "")).isdigit() else None,
        "cor": item.get("cor"),
        "capacidade": int(item["capacidade"]) if str(item.get("capacidade", "")).isdigit() else None,
        "bagagens": str(item.get("bagagens", "")),
        "aplicacao": item.get("aplicacao"),
        "status": item.get("status", "Ativo"),
        "portal_publicado": str(item.get("portal_publicado", True)).lower() not in {"nao", "false", "0"},
        "veiculo_de_rede": str(item.get("veiculo_de_rede", "")).strip() or None,
        "dados_extra": _extra(item, known),
    }
    rede = str(item.get("veiculo_de_rede", "")).strip().lower()
    if rede in {"sim", "true", "1", "yes"}:
        row["veiculo_de_rede"] = "Sim"
        row["portal_publicado"] = True
    elif rede in {"nao", "false", "0", "no"}:
        row["veiculo_de_rede"] = "Nao"
        row["portal_publicado"] = False
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_operational_point_row(item):
    known = KNOWN_COLUMNS["operational_points"]
    row = {
        "legacy_admin_id": item.get("id"),
        "nome": item.get("nome"),
        "tipo": item.get("tipo"),
        "estado_uf": item.get("estado_uf") or item.get("estado"),
        "cidade_nome": item.get("cidade_nome") or item.get("cidade"),
        "endereco": item.get("endereco"),
        "website_slug": item.get("website_slug"),
        "website_path": item.get("website_path"),
        "status": item.get("status", "Operando"),
        "portal_publicado": bool(item.get("portal_publicado", True)),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_transport_request_row(item, resolver: RefResolver):
    known = KNOWN_COLUMNS["transport_requests"]
    row = {
        "legacy_admin_id": item.get("id"),
        "origem": item.get("origem"),
        "destino": item.get("destino"),
        "data": item.get("data"),
        "hora": item.get("hora"),
        "passageiros": str(item.get("passageiros", "")),
        "categoria": item.get("veiculo_categoria") or item.get("categoria"),
        "status": item.get("status", "Recebida"),
        "approval_status": item.get("approval_status"),
        "origem_fonte": item.get("origem_fonte"),
        "observacoes": item.get("observacoes"),
        "partner_slug": item.get("partner_slug"),
        "partner_code": item.get("partner_code"),
        "contributor_code": item.get("contributor_code") or item.get("contributor_ref"),
        "source": item.get("source"),
        "flow": item.get("flow"),
        "canal_origem": item.get("canal_origem"),
        "via_qr": bool(item.get("via_qr", False)),
        "nome": item.get("nome"),
        "telefone": item.get("telefone"),
        "email": item.get("email"),
        "valor_estimado": parse_money(item.get("valor_estimado")),
        "partner_id": resolver.uuid(item.get("partner_id")),
        "contributor_id": resolver.uuid(item.get("contributor_id")),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_reservation_row(item, resolver: RefResolver):
    known = KNOWN_COLUMNS["reservations"]
    data_raw = str(item.get("data", ""))
    hora = ""
    data = data_raw
    if " " in data_raw:
        parts = data_raw.split(" ", 1)
        data, hora = parts[0], parts[1]
    row = {
        "legacy_admin_id": item.get("id"),
        "numero": item.get("numero"),
        "cliente": item.get("cliente"),
        "empresa": item.get("empresa"),
        "trajeto": item.get("trajeto"),
        "origem": item.get("origem"),
        "destino": item.get("destino"),
        "data": data,
        "hora": hora,
        "status": item.get("status", "Pendente"),
        "valor": parse_money(item.get("valor")),
        "tipo": item.get("tipo"),
        "observacoes": item.get("observacoes"),
        "motorista": item.get("motorista"),
        "partner_slug": item.get("partner_slug"),
        "partner_code": item.get("partner_code"),
        "contributor_code": item.get("contributor_code") or item.get("contributor_ref"),
        "source": item.get("source"),
        "flow": item.get("flow"),
        "canal_origem": item.get("canal_origem"),
        "via_qr": bool(item.get("via_qr", False)),
        "transport_request_legacy_id": item.get("transport_request_id"),
        "partner_id": resolver.uuid(item.get("partner_id")),
        "contributor_id": resolver.uuid(item.get("contributor_id")),
        "driver_id": resolver.uuid(item.get("driver_id")),
        "company_id": resolver.uuid(item.get("company_id")),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_network_commission_row(item, resolver: RefResolver):
    known = KNOWN_COLUMNS["network_commissions"]
    row = {
        "legacy_admin_id": item.get("id"),
        "partner_id": resolver.uuid(item.get("partner_id")),
        "reservation_numero": item.get("reservation_numero"),
        "valor_base": float(item.get("valor_base", 0) or 0),
        "percentual": float(item.get("percentual", 0) or 0),
        "valor_bruto": float(item.get("valor_bruto", 0) or 0),
        "valor_comissao": float(item.get("valor_comissao", 0) or 0),
        "status_pagamento": item.get("status_pagamento", "pendente"),
        "dados_extra": _extra(item, known),
    }
    res_uuid = resolver.uuid(item.get("reservation_id"))
    if res_uuid:
        row["reservation_id"] = res_uuid
    treq_uuid = resolver.uuid(item.get("transport_request_id"))
    if treq_uuid:
        row["transport_request_id"] = treq_uuid
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_contributor_commission_row(item, resolver: RefResolver):
    known = KNOWN_COLUMNS["contributor_commissions"]
    row = {
        "legacy_admin_id": item.get("id"),
        "partner_id": resolver.uuid(item.get("partner_id")),
        "contributor_id": resolver.uuid(item.get("contributor_id")),
        "reservation_numero": item.get("reservation_numero"),
        "percentual": float(item.get("percentual", 0) or 0),
        "valor_comissao": float(item.get("valor_comissao", 0) or 0),
        "status_pagamento": item.get("status_pagamento", "pendente"),
        "dados_extra": _extra(item, known),
    }
    res_uuid = resolver.uuid(item.get("reservation_id"))
    if res_uuid:
        row["reservation_id"] = res_uuid
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_audit_log_row(item, resolver: RefResolver):
    known = KNOWN_COLUMNS["audit_log"]
    row = {
        "legacy_admin_id": item.get("id"),
        "action": item.get("action"),
        "actor_type": item.get("actor_type", "system"),
        "actor_id": item.get("actor_id"),
        "partner_id": resolver.uuid(item.get("partner_id")),
        "record_table": item.get("record_table"),
        "record_id": item.get("record_id") or str(item.get("payload", {}).get("reservation_id", "")),
        "payload": item.get("payload") or {},
        "ip_address": item.get("ip_address"),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_company_lead_row(item):
    known = KNOWN_COLUMNS["company_leads"]
    row = {
        "legacy_admin_id": item.get("id"),
        "empresa": item.get("empresa"),
        "responsavel": item.get("responsavel"),
        "telefone": item.get("telefone"),
        "email": item.get("email"),
        "cidade": item.get("cidade"),
        "estado": item.get("estado"),
        "estado_uf": item.get("estado_uf") or item.get("estado"),
        "origem": item.get("origem"),
        "status": item.get("status", "Novo"),
        "observacoes": item.get("observacoes"),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_driver_lead_row(item):
    known = KNOWN_COLUMNS["driver_leads"]
    row = {
        "legacy_admin_id": item.get("id"),
        "nome": item.get("nome"),
        "telefone": item.get("telefone"),
        "email": item.get("email"),
        "cidade": item.get("cidade"),
        "estado": item.get("estado"),
        "estado_uf": item.get("estado_uf") or item.get("estado"),
        "origem": item.get("origem"),
        "status": item.get("status", "Novo"),
        "observacoes": item.get("observacoes"),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_event_log_row(item, *, legacy_override=None):
    known = KNOWN_COLUMNS["event_log"]
    legacy = legacy_override or item.get("id")
    row = {
        "legacy_admin_id": legacy,
        "tipo": item.get("tipo"),
        "titulo": item.get("titulo"),
        "resumo": item.get("resumo"),
        "origem": item.get("origem"),
        "referencia_id": item.get("referencia_id"),
        "user_type": item.get("user_type"),
        "user_id": item.get("user_id"),
        "payload": item.get("payload") or {},
    }
    extra = _extra(item, known)
    if item.get("criado_em"):
        extra["criado_em"] = item["criado_em"]
    if extra:
        row["payload"] = {**(row.get("payload") or {}), **extra}
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_company_row(item):
    known = {
        "legacy_admin_id", "portal_key", "tipo_pessoa", "razao_social", "nome_fantasia", "cnpj",
        "inscricao_estadual", "email", "telefone", "telefone_2", "responsavel", "estado", "cidade",
        "portal_ativo", "status_empresa", "portal_link", "portal_criado_em", "dados_extra",
    }
    row = {
        "legacy_admin_id": item.get("id"),
        "portal_key": item.get("portal_key"),
        "tipo_pessoa": item.get("tipo_pessoa", "juridica"),
        "razao_social": item.get("razao_social"),
        "nome_fantasia": item.get("nome_fantasia") or item.get("nome"),
        "cnpj": item.get("cnpj") or item.get("cpf_cnpj"),
        "inscricao_estadual": item.get("inscricao_estadual"),
        "email": item.get("email"),
        "telefone": item.get("telefone"),
        "telefone_2": item.get("telefone_2"),
        "responsavel": item.get("responsavel"),
        "estado": item.get("estado") or item.get("uf"),
        "cidade": item.get("cidade"),
        "portal_ativo": bool(item.get("portal_ativo", True)),
        "status_empresa": item.get("status_empresa", "Ativa"),
        "portal_link": item.get("portal_link"),
        "portal_criado_em": item.get("portal_criado_em"),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_master_client_row(item):
    known = {"legacy_admin_id", "tipo_pessoa", "nome_completo", "cpf_cnpj", "email", "telefone", "estado", "dados_extra"}
    row = {
        "legacy_admin_id": item.get("id"),
        "tipo_pessoa": item.get("tipo_pessoa", "fisica"),
        "nome_completo": item.get("nome_completo") or item.get("nome"),
        "cpf_cnpj": item.get("cpf_cnpj") or item.get("cpf"),
        "email": item.get("email"),
        "telefone": item.get("telefone"),
        "estado": item.get("estado") or item.get("uf"),
        "dados_extra": _extra(item, known),
    }
    if item.get("uuid"):
        row["id"] = item["uuid"]
    return {k: v for k, v in row.items() if v is not None}


def to_catalog_row(item, collection_key):
    return {
        "collection_key": collection_key,
        "legacy_admin_id": item.get("id"),
        "payload": item,
    }


TO_ROW = {
    "partner_networks": to_partner_network_row,
    "network_contributors": to_network_contributor_row,
    "drivers": to_driver_row,
    "vehicles": to_vehicle_row,
    "operational_points": to_operational_point_row,
    "transport_requests": to_transport_request_row,
    "reservations": to_reservation_row,
    "network_commissions": to_network_commission_row,
    "contributor_commissions": to_contributor_commission_row,
    "audit_log": to_audit_log_row,
    "company_leads": to_company_lead_row,
    "driver_leads": to_driver_lead_row,
}


def from_db_row(row):
    return _merge_row(row)


def from_catalog_row(row):
    payload = deepcopy(row.get("payload") or {})
    if row.get("legacy_admin_id"):
        payload["id"] = row["legacy_admin_id"]
    if row.get("id"):
        payload["uuid"] = row["id"]
    return payload
