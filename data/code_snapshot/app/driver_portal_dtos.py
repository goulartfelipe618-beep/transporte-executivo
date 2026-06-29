"""DTOs sanitizados para o Portal Motorista — nunca expor dados internos."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

DRIVER_PORTAL_STATUSES = [
    "Pendente",
    "Aceitar",
    "Confirmada",
    "Em deslocamento",
    "Em atendimento",
    "Concluida",
    "Concluído",
    "Cancelada",
    "Cancelado",
]

STATUS_ACTIONS = [
    {"key": "Aceitar", "label": "Aceitar", "status": "Confirmada"},
    {"key": "Em deslocamento", "label": "Em deslocamento", "status": "Em deslocamento"},
    {"key": "Em atendimento", "label": "Em atendimento", "status": "Em atendimento"},
    {"key": "Concluido", "label": "Concluído", "status": "Concluida"},
    {"key": "Cancelado", "label": "Cancelado", "status": "Cancelada"},
]


def normalize_identifier(value):
    return re.sub(r"\D", "", str(value or ""))


def mask_cpf(value):
    digits = normalize_identifier(value)
    if len(digits) != 11:
        return str(value or "")
    return f"{digits[:3]}.***.***-{digits[-2:]}"


def parse_trajeto(trajeto):
    raw = str(trajeto or "")
    if "| Volta:" in raw:
        raw = raw.split("| Volta:")[0]
    parts = raw.split("->")
    origem = parts[0].strip() if parts else ""
    destino = parts[1].strip() if len(parts) > 1 else ""
    return origem, destino


def maps_route_url(origem, destino=None):
    query = origem if not destino else f"{origem} to {destino}"
    from urllib.parse import quote

    return f"https://maps.google.com/?q={quote(query)}"


def parse_money_value(value):
    raw = str(value or "").strip()
    if not raw:
        return 0.0
    cleaned = re.sub(r"[^\d,.-]", "", raw)
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def money_display(value):
    return f"R$ {float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def find_company_name(app, reservation):
    company_id = reservation.get("company_id")
    if company_id:
        for client in getattr(app, "clients", []):
            if str(client.get("id", "")) == str(company_id):
                return client.get("razao_social") or client.get("nome_fantasia") or client.get("nome", "")
    return reservation.get("empresa") or reservation.get("cliente", "")


def reservation_dto(app, reservation, driver=None):
    if driver is not None:
        from .driver_portal_panel import is_driver_owned_reservation
    owned = bool(driver is not None and is_driver_owned_reservation(reservation, driver))
    origem, destino = parse_trajeto(reservation.get("trajeto"))
    esconder_valores = str(reservation.get("esconder_valores") or "").strip().lower() in {"1", "true", "yes", "sim", "on"}
    return {
        "numero": reservation.get("numero"),
        "cliente": reservation.get("cliente"),
        "empresa": find_company_name(app, reservation),
        "data": reservation.get("data"),
        "hora": reservation.get("hora") or "",
        "origem": origem,
        "destino": destino,
        "trajeto": reservation.get("trajeto"),
        "status": reservation.get("status") or "Pendente",
        "observacoes": reservation.get("observacoes", ""),
        "tipo": reservation.get("tipo", ""),
        "driver_id": reservation.get("driver_id"),
        "owner_type": reservation.get("owner_type") or ("motorista" if owned else "operacao"),
        "owned_by_driver": owned,
        "source_label": "Minha" if owned else "Atribuida",
        "can_edit": owned and str(reservation.get("status", "")).lower() not in {"concluida", "concluído", "concluido", "cancelada", "cancelado"},
        "valores_ocultos": esconder_valores,
        "maps_url": maps_route_url(origem, destino if destino else None),
    }


def reservation_dto_legacy(reservation):
    """Compatibilidade /api/driver/reservations — campos originais + extras opcionais."""
    dto = {
        "numero": reservation.get("numero"),
        "cliente": reservation.get("cliente"),
        "data": reservation.get("data"),
        "trajeto": reservation.get("trajeto"),
        "status": reservation.get("status"),
        "driver_id": reservation.get("driver_id"),
    }
    return dto


def profile_dto(driver):
    return {
        "id": driver.get("id", ""),
        "nome": driver.get("nome", ""),
        "cpf": driver.get("cpf", ""),
        "cpf_masked": mask_cpf(driver.get("cpf")),
        "telefone": driver.get("telefone", ""),
        "email": driver.get("email", ""),
        "cidade": driver.get("cidade", ""),
        "estado": driver.get("estado", ""),
        "validade_cnh": driver.get("validade_cnh", ""),
        "portal_ativo": bool(driver.get("portal_ativo")),
        "documents": {
            "cnh": {
                "label": "CNH",
                "validade": driver.get("validade_cnh", ""),
                "status": "cadastrado" if driver.get("cnh_foto") or driver.get("validade_cnh") else "pendente",
                "upload_enabled": False,
            },
            "crlv": {"label": "CRLV", "status": "pendente", "upload_enabled": False},
            "seguro": {"label": "Seguro", "status": "pendente", "upload_enabled": False},
        },
    }


def _parse_reservation_date(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:10] if fmt == "%d/%m/%Y" else raw, fmt).date()
        except ValueError:
            continue
    return None


def dashboard_dto(app, driver, session):
    from .portal_auth import driver_reservations_for

    today = datetime.now().date()
    week_end = today + timedelta(days=7)
    month_end = today + timedelta(days=30)
    reservations = [reservation_dto(app, r, driver) for r in driver_reservations_for(app, driver)]
    own = [r for r in reservations if r.get("owned_by_driver")]
    assigned = [r for r in reservations if not r.get("owned_by_driver")]

    def bucket(item):
        dt = _parse_reservation_date(item.get("data"))
        if not dt:
            return "other"
        if dt == today:
            return "today"
        if today < dt <= week_end:
            return "week"
        if today < dt <= month_end:
            return "month"
        return "other"

    today_items = [r for r in reservations if bucket(r) == "today"]
    upcoming = [r for r in reservations if bucket(r) in {"today", "week"}]
    done = [r for r in reservations if str(r.get("status", "")).lower() in {"concluida", "concluído", "concluido"}]
    pending = [r for r in reservations if str(r.get("status", "")).lower() in {"pendente", "aceitar", "confirmada"}]

    return {
        "cards": {
            "hoje": len(today_items),
            "proximas": len(upcoming),
            "concluidas": len(done),
            "pendentes": len(pending),
            "minhas": len(own),
            "atribuidas": len(assigned),
        },
        "indicators": {
            "portal_status": "Ativo" if driver.get("portal_ativo") else "Inativo",
            "ultimo_acesso": session.get("last_activity") or session.get("created_at", ""),
            "cidade_principal": driver.get("cidade", ""),
            "estado": driver.get("estado", ""),
        },
        "proximas_reservas": upcoming[:5],
    }


def driver_finance_dto(app, driver):
    from .portal_auth import driver_reservations_for

    reservations = [reservation_dto(app, r, driver) | dict(raw=r) for r in driver_reservations_for(app, driver)]
    items = []
    own_total = 0.0
    assigned_total = 0.0
    open_total = 0.0
    done_total = 0.0

    for item in reservations:
        raw = item.pop("raw")
        status = str(item.get("status") or "").lower()
        canceled = status in {"cancelada", "cancelado"}
        done = status in {"concluida", "concluído", "concluido"}
        owned = bool(item.get("owned_by_driver"))
        hidden = bool(item.get("valores_ocultos")) and not owned
        value_source = raw.get("valor") if owned else (raw.get("repasse") or raw.get("valor"))
        amount = 0.0 if hidden else parse_money_value(value_source)
        if not canceled:
            if owned:
                own_total += amount
            else:
                assigned_total += amount
            if done:
                done_total += amount
            else:
                open_total += amount
        items.append(
            {
                "numero": item.get("numero"),
                "data": item.get("data"),
                "cliente": item.get("cliente"),
                "trajeto": item.get("trajeto"),
                "status": item.get("status"),
                "origem": item.get("origem"),
                "destino": item.get("destino"),
                "tipo": "Propria" if owned else "Atribuida",
                "valor": "Sob consulta" if hidden else money_display(amount),
                "valor_num": amount,
                "owned_by_driver": owned,
                "valores_ocultos": hidden,
            }
        )

    return {
        "cards": {
            "receita_propria": money_display(own_total),
            "repasse_atribuido": money_display(assigned_total),
            "em_aberto": money_display(open_total),
            "concluido": money_display(done_total),
        },
        "items": items,
    }


def portal_branding(app):
    from .settings_store import load_settings
    from .cdn.urls import resolve_media_url
    from .version import APP_BUILD

    settings = load_settings()
    return {
        "empresa": settings.get("nome_projeto") or settings.get("empresa") or "Nexus Transfer",
        "logo_url": resolve_media_url(settings.get("logo_global") or ""),
        "build": APP_BUILD,
    }
