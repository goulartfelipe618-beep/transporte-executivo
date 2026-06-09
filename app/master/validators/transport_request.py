"""Validadores do modulo Solicitacoes — sem Tkinter."""
from __future__ import annotations

from app.platform import TRANSPORT_REQUEST_STATUSES

REQUEST_ERROR_MESSAGES = {
    "solicitacao_nao_encontrada": "Solicitacao nao encontrada.",
    "origem_obrigatoria": "Informe a origem.",
    "destino_obrigatorio": "Informe o destino.",
    "nome_obrigatorio": "Informe o nome do solicitante.",
    "status_invalido": "Status invalido.",
}


def validate_transport_request_form(data, *, is_create=False):
    errors = []
    if not str(data.get("origem", "")).strip():
        errors.append(REQUEST_ERROR_MESSAGES["origem_obrigatoria"])
    if not str(data.get("destino", "")).strip():
        errors.append(REQUEST_ERROR_MESSAGES["destino_obrigatorio"])
    if not str(data.get("nome", "")).strip():
        errors.append(REQUEST_ERROR_MESSAGES["nome_obrigatorio"])
    status = str(data.get("status", "")).strip()
    if status and status not in TRANSPORT_REQUEST_STATUSES:
        errors.append(REQUEST_ERROR_MESSAGES["status_invalido"])
    return errors


def map_service_error(code):
    return REQUEST_ERROR_MESSAGES.get(str(code or ""), str(code or "Erro ao processar solicitacao."))
