"""Servico de automacoes — espelha app.automations sem alterar o modulo legado."""
from __future__ import annotations

import secrets
from datetime import datetime

from app.automations import (
    AUTOMATION_TYPES,
    TOKEN_BYTES,
    automation_url,
    ensure_automations_loaded,
    normalize_domain,
    save_automations,
)


def _rows(runtime):
    ensure_automations_loaded(runtime)
    return list(getattr(runtime, "automations", []) or [])


def automation_display(item):
    tipo = str(item.get("tipo") or "")
    return {
        **item,
        "tipo_label": AUTOMATION_TYPES.get(tipo, tipo),
        "url": automation_url(item.get("token", "")),
        "status_label": "Ativo" if item.get("ativo") else "Desativado",
        "domain_label": item.get("dominio_permitido") or "Bloqueado ate configurar",
        "tests_count": len(item.get("tests") or []),
    }


def list_automations(runtime):
    return [automation_display(item) for item in _rows(runtime)]


def list_summary(runtime):
    rows = list_automations(runtime)
    return {
        "total": len(rows),
        "ativos": sum(1 for row in rows if row.get("ativo")),
        "desativados": sum(1 for row in rows if not row.get("ativo")),
        "transfer": sum(1 for row in rows if row.get("tipo") == "transfer_request"),
        "motorista": sum(1 for row in rows if row.get("tipo") == "driver_request"),
    }


def find_automation(runtime, token):
    token = str(token or "").strip()
    if not token:
        return None
    for item in _rows(runtime):
        if str(item.get("token")) == token:
            return automation_display(item)
    return None


def validate_create_form(form_data):
    nome = str(form_data.get("nome", "")).strip()
    tipo = str(form_data.get("tipo", "")).strip()
    errors = []
    if not nome:
        errors.append("Informe o nome da automacao.")
    if tipo not in AUTOMATION_TYPES:
        errors.append("Selecione um dos 2 tipos permitidos.")
    return errors, nome, tipo


def create_automation(runtime, form_data):
    errors, nome, tipo = validate_create_form(form_data)
    if errors:
        return None, errors
    ensure_automations_loaded(runtime)
    item = {
        "nome": nome,
        "tipo": tipo,
        "token": secrets.token_urlsafe(TOKEN_BYTES),
        "ativo": True,
        "dominio_permitido": "",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "tests": [],
    }
    runtime.automations.append(item)
    save_automations(runtime)
    return item, []


def validate_domain_form(form_data):
    domain = normalize_domain(str(form_data.get("dominio_permitido", "")).strip())
    if not domain:
        return ["Informe um dominio valido, como https://seudominio.com."], ""
    return [], domain


def update_domain(runtime, token, form_data):
    item = find_automation(runtime, token)
    if not item:
        return None, ["Automacao nao encontrada."]
    errors, domain = validate_domain_form(form_data)
    if errors:
        return None, errors
    raw = next((row for row in _rows(runtime) if str(row.get("token")) == token), None)
    if not raw:
        return None, ["Automacao nao encontrada."]
    raw["dominio_permitido"] = domain
    save_automations(runtime)
    return automation_display(raw), []


def toggle_automation(runtime, token):
    raw = next((row for row in _rows(runtime) if str(row.get("token")) == token), None)
    if not raw:
        return None, ["Automacao nao encontrada."]
    raw["ativo"] = not raw.get("ativo", True)
    save_automations(runtime)
    return automation_display(raw), []


def delete_automation(runtime, token):
    rows = _rows(runtime)
    raw = next((row for row in rows if str(row.get("token")) == token), None)
    if not raw:
        return False, ["Automacao nao encontrada."]
    runtime.automations = [row for row in rows if str(row.get("token")) != token]
    save_automations(runtime)
    return True, []


def type_choices():
    return [{"key": key, "label": label} for key, label in AUTOMATION_TYPES.items()]
