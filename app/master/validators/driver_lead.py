"""Validadores do modulo Leads de Motoristas — sem Tkinter."""
from __future__ import annotations

from app.platform import DRIVER_LEAD_STATUSES

DRIVER_LEAD_ERROR_MESSAGES = {
    "lead_motorista_nao_encontrado": "Lead de motorista nao encontrado.",
    "nome_obrigatorio": "Informe o nome do motorista.",
    "telefone_obrigatorio": "Informe o telefone.",
    "status_invalido": "Status invalido.",
}


def validate_driver_lead_form(data, *, is_create=False):
    errors = []
    if not str(data.get("nome", "")).strip():
        errors.append(DRIVER_LEAD_ERROR_MESSAGES["nome_obrigatorio"])
    if not str(data.get("telefone", "")).strip():
        errors.append(DRIVER_LEAD_ERROR_MESSAGES["telefone_obrigatorio"])
    status = str(data.get("status", "")).strip()
    if status and status not in DRIVER_LEAD_STATUSES:
        errors.append(DRIVER_LEAD_ERROR_MESSAGES["status_invalido"])
    return errors


def map_service_error(code):
    return DRIVER_LEAD_ERROR_MESSAGES.get(str(code or ""), str(code or "Erro ao processar lead de motorista."))
