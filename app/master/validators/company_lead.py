"""Validadores do modulo Leads de Empresas — sem Tkinter."""
from __future__ import annotations

from app.platform import COMPANY_LEAD_STATUSES

COMPANY_LEAD_ERROR_MESSAGES = {
    "lead_empresa_nao_encontrado": "Lead de empresa nao encontrado.",
    "empresa_obrigatoria": "Informe o nome da empresa.",
    "responsavel_obrigatorio": "Informe o responsavel.",
    "status_invalido": "Status invalido.",
}


def validate_company_lead_form(data, *, is_create=False):
    errors = []
    if not str(data.get("empresa", "")).strip():
        errors.append(COMPANY_LEAD_ERROR_MESSAGES["empresa_obrigatoria"])
    if not str(data.get("responsavel", "")).strip():
        errors.append(COMPANY_LEAD_ERROR_MESSAGES["responsavel_obrigatorio"])
    status = str(data.get("status", "")).strip()
    if status and status not in COMPANY_LEAD_STATUSES:
        errors.append(COMPANY_LEAD_ERROR_MESSAGES["status_invalido"])
    return errors


def map_service_error(code):
    return COMPANY_LEAD_ERROR_MESSAGES.get(str(code or ""), str(code or "Erro ao processar lead de empresa."))
