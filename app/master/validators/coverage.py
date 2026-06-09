"""Validadores do modulo Abrangencia — sem Tkinter."""
from __future__ import annotations

from app.geography import OPERATIONAL_POINT_STATUSES, OPERATIONAL_POINT_TYPES

COVERAGE_ERROR_MESSAGES = {
    "ponto_nao_encontrado": "Ponto operacional nao encontrado.",
    "nome_obrigatorio": "Informe o nome do ponto operacional.",
    "estado_obrigatorio": "Selecione o estado (IBGE).",
    "cidade_obrigatoria": "Selecione a cidade (IBGE).",
    "tipo_invalido": "Tipo de ponto operacional invalido.",
    "status_invalido": "Status invalido.",
}


def validate_coverage_form(data, *, is_create=False):
    errors = []
    if not str(data.get("nome", "")).strip():
        errors.append(COVERAGE_ERROR_MESSAGES["nome_obrigatorio"])
    uf = str(data.get("estado_uf", "")).strip().upper()
    if is_create and len(uf) != 2:
        errors.append(COVERAGE_ERROR_MESSAGES["estado_obrigatorio"])
    if is_create:
        try:
            cidade_id = int(data.get("cidade_ibge_id") or 0)
        except (TypeError, ValueError):
            cidade_id = 0
        if cidade_id <= 0:
            errors.append(COVERAGE_ERROR_MESSAGES["cidade_obrigatoria"])
    tipo = str(data.get("tipo", "")).strip()
    if tipo and tipo not in OPERATIONAL_POINT_TYPES:
        errors.append(COVERAGE_ERROR_MESSAGES["tipo_invalido"])
    status = str(data.get("status", "")).strip()
    if status and status not in OPERATIONAL_POINT_STATUSES:
        errors.append(COVERAGE_ERROR_MESSAGES["status_invalido"])
    return errors


def map_service_error(code):
    return COVERAGE_ERROR_MESSAGES.get(str(code or ""), str(code or "Erro ao processar solicitacao."))
