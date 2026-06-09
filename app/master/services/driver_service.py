"""CRUD de motoristas — logica extraida de pages.py (sem Tkinter)."""
from __future__ import annotations

from datetime import datetime

from app.portal_auth import find_driver_by_id, normalize_driver_record
from app.portal_server import driver_key

from .driver_portal_service import driver_reservations, portal_info, portal_last_access, refresh_activation_token

DONE_STATUSES = {"concluida", "concluído", "concluido", "finalizada"}
CANCEL_STATUSES = {"cancelada", "cancelado", "rejeitada"}
OPEN_STATUSES = {"pendente", "confirmada", "aceitar", "em deslocamento", "em atendimento"}


def driver_display_name(driver):
    return str(driver.get("nome", "")).strip()


def list_drivers(app, *, search="", include_blocked=True):
    items = []
    query = str(search or "").strip().lower()
    for driver in getattr(app, "drivers", []) or []:
        frota = str(driver.get("frota", "Ativo"))
        if not include_blocked and frota.lower() in {"bloqueado", "inativo"}:
            continue
        if query:
            haystack = " ".join(
                [
                    driver.get("nome", ""),
                    driver.get("cpf", ""),
                    driver.get("telefone", ""),
                    driver.get("email", ""),
                    driver.get("cidade", ""),
                    driver.get("id", ""),
                ]
            ).lower()
            if query not in haystack:
                continue
        items.append(driver)
    items.sort(key=lambda row: driver_display_name(row).lower())
    return items


def find_driver_by_id_local(app, driver_id):
    return find_driver_by_id(app, driver_id)


def _build_driver_payload(form_data, *, existing=None):
    existing = existing or {}
    payload = dict(existing)
    fields = [
        "nome",
        "cpf",
        "rg",
        "nascimento",
        "telefone",
        "email",
        "estado",
        "cidade",
        "cidade_filtro",
        "cep",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cnh",
        "categoria",
        "validade_cnh",
        "frota",
        "observacoes_motorista",
        "tipo_pagamento",
        "pix_chave",
        "banco",
        "agencia",
        "conta",
        "titular",
        "cpf_titular",
        "observacoes_pagamento",
        "foto_perfil",
        "cnh_frente",
        "cnh_verso",
        "comprovante_residencia",
    ]
    for key in fields:
        if key in form_data:
            payload[key] = str(form_data.get(key, "")).strip()
    payload["portal_slug"] = driver_key(payload)
    payload["endereco_completo"] = ", ".join(
        part
        for part in [
            payload.get("logradouro"),
            payload.get("numero"),
            payload.get("bairro"),
            payload.get("cidade"),
            payload.get("estado"),
            payload.get("cep"),
        ]
        if str(part or "").strip()
    )
    portal_label = "Senha OK" if existing.get("password_hash") else "Pendente"
    payload.setdefault("portal", portal_label)
    return payload


def create_driver(app, form_data):
    drivers = getattr(app, "drivers", []) or []
    payload = _build_driver_payload(form_data)
    payload["data"] = datetime.now().strftime("%d/%m/%Y")
    payload = normalize_driver_record(payload, drivers)
    from .driver_portal_service import get_portal_link

    payload["link"] = get_portal_link(payload)
    payload["portal_link"] = payload["link"]
    drivers.insert(0, payload)
    app.drivers = drivers
    if hasattr(app, "save_state"):
        app.save_state()
    return payload


def update_driver(app, driver_id, form_data):
    driver = find_driver_by_id(app, driver_id)
    if not driver:
        raise ValueError("motorista_nao_encontrado")
    payload = _build_driver_payload(form_data, existing=driver)
    payload = normalize_driver_record({**driver, **payload}, getattr(app, "drivers", []) or [])
    from .driver_portal_service import get_portal_link

    payload["link"] = get_portal_link(payload)
    payload["portal_link"] = payload["link"]
    driver.update(payload)
    if hasattr(app, "save_state"):
        app.save_state()
    return driver


def block_driver(app, driver_id):
    driver = find_driver_by_id(app, driver_id)
    if not driver:
        raise ValueError("motorista_nao_encontrado")
    driver["frota"] = "Bloqueado"
    driver["portal_ativo"] = False
    driver["portal"] = "Bloqueado"
    if hasattr(app, "save_state"):
        app.save_state()
    return driver


def activate_driver(app, driver_id, *, regenerate_token=True):
    driver = find_driver_by_id(app, driver_id)
    if not driver:
        raise ValueError("motorista_nao_encontrado")
    driver["frota"] = "Ativo"
    token = ""
    if regenerate_token and not driver.get("password_hash"):
        token = refresh_activation_token(driver)
    elif not driver.get("activation_token") and not driver.get("password_hash"):
        token = refresh_activation_token(driver)
    if driver.get("password_hash"):
        driver["portal_ativo"] = True
        driver["portal"] = "Senha OK"
    else:
        driver["portal"] = "Pendente"
    if hasattr(app, "save_state"):
        app.save_state()
    return driver, token


def driver_stats(app, driver):
    reservations = driver_reservations(app, driver)
    total = len(reservations)
    done = cancelled = pending = 0
    last_activity = portal_last_access(app, driver) or ""
    for item in reservations:
        status = str(item.get("status", "")).strip().lower().replace("í", "i")
        if status in DONE_STATUSES:
            done += 1
        elif status in CANCEL_STATUSES:
            cancelled += 1
        elif status in OPEN_STATUSES or status:
            pending += 1
        stamp = str(item.get("atualizado_em") or item.get("data") or "")
        if stamp and (not last_activity or stamp > last_activity):
            last_activity = stamp
    return {
        "total_reservas": total,
        "reservas_concluidas": done,
        "reservas_canceladas": cancelled,
        "reservas_pendentes": pending,
        "ultima_atividade": last_activity or "—",
        "portal": portal_info(driver),
    }


def list_summary(app):
    drivers = list_drivers(app, include_blocked=True)
    active = sum(1 for d in drivers if str(d.get("frota", "")).lower() in {"ativo", "homologado", "operando"})
    blocked = sum(1 for d in drivers if str(d.get("frota", "")).lower() in {"bloqueado", "inativo"})
    portal_ok = sum(1 for d in drivers if d.get("password_hash") and d.get("portal_ativo"))
    return {"total": len(drivers), "ativos": active, "bloqueados": blocked, "portal_ativado": portal_ok}
