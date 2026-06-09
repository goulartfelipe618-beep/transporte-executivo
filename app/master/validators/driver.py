"""Validadores do modulo Motoristas — sem Tkinter."""
from __future__ import annotations

import re

from .input import is_valid_email

DRIVER_ERROR_MESSAGES = {
    "motorista_nao_encontrado": "Motorista nao encontrado.",
    "nome_obrigatorio": "Informe o nome do motorista.",
    "cpf_obrigatorio": "Informe o CPF do motorista.",
}

FROTA_OPTIONS = ["Ativo", "Homologado", "Operando", "Inativo", "Bloqueado", "Em analise"]
PAYMENT_OPTIONS = ["PIX", "Transferencia bancaria", "Dinheiro", "Outro"]


def normalize_cpf(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 11:
        return str(value or "").strip()
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def validate_driver_form(data, *, is_create=False):
    errors = []
    nome = str(data.get("nome", "")).strip()
    cpf = str(data.get("cpf", "")).strip()
    if not nome:
        errors.append(DRIVER_ERROR_MESSAGES["nome_obrigatorio"])
    if not cpf:
        errors.append(DRIVER_ERROR_MESSAGES["cpf_obrigatorio"])
    email = str(data.get("email", "")).strip()
    if email and not is_valid_email(email):
        errors.append("E-mail invalido.")
    frota = str(data.get("frota", "")).strip()
    if frota and frota not in FROTA_OPTIONS:
        errors.append("Status da frota invalido.")
    return errors


def map_service_error(code):
    return DRIVER_ERROR_MESSAGES.get(str(code or ""), str(code or "Erro ao processar solicitacao."))
