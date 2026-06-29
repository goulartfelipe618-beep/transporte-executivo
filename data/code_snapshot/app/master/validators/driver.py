"""Validadores do modulo Motoristas — sem Tkinter."""
from __future__ import annotations

import re

from .input import is_valid_email
from ..services.location_service import city_options, validate_location_fields

DRIVER_ERROR_MESSAGES = {
    "motorista_nao_encontrado": "Motorista nao encontrado.",
    "nome_obrigatorio": "Informe o nome do motorista.",
    "cpf_obrigatorio": "Informe o CPF do motorista.",
}

FROTA_OPTIONS = ["Ativo", "Homologado", "Operando", "Inativo", "Bloqueado", "Em analise"]
PAYMENT_OPTIONS = ["PIX", "Transferencia bancaria", "Dinheiro", "Outro"]
CNH_CATEGORY_OPTIONS = ["ACC", "A", "B", "C", "D", "E", "AB", "AC", "AD", "AE"]

CPF_RE = re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")
PHONE_RE = re.compile(r"^\(\d{2}\) \d \d{4}-\d{4}$")
DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
CNH_VALIDITY_RE = re.compile(r"^\d{2}/\d{4}$")


def normalize_cpf(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 11:
        return str(value or "").strip()
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def normalize_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 11:
        return str(value or "").strip()
    return f"({digits[:2]}) {digits[2]} {digits[3:7]}-{digits[7:]}"


def normalize_driver_form(data):
    """Normaliza campos digitados no formulario web antes de validar/persistir."""
    normalized = dict(data or {})
    keep_case = {"frota", "tipo_pagamento"}
    for key, value in list(normalized.items()):
        text = str(value or "").strip()
        normalized[key] = text if key in keep_case else text.upper()
    normalized["cpf"] = normalize_cpf(normalized.get("cpf", ""))
    normalized["telefone"] = normalize_phone(normalized.get("telefone", ""))
    normalized["email"] = str(normalized.get("email", "")).strip().upper()
    normalized["estado_uf"] = str(normalized.get("estado_uf") or normalized.get("estado") or "").strip().upper()
    normalized["estado"] = normalized["estado_uf"]
    normalized["cidade_nome"] = str(normalized.get("cidade_nome") or normalized.get("cidade") or "").strip().upper()
    normalized["cidade"] = normalized["cidade_nome"]
    normalized["cnh"] = re.sub(r"\D", "", str(normalized.get("cnh", "")))
    normalized["categoria"] = str(normalized.get("categoria", "")).strip().upper()
    return normalized


def _valid_ibge_city(data):
    uf = str(data.get("estado_uf") or data.get("estado") or "").upper().strip()
    try:
        city_id = int(data.get("cidade_ibge_id") or 0)
    except (TypeError, ValueError):
        return False
    if not uf or city_id <= 0:
        return False
    return any(int(city.get("id") or 0) == city_id for city in city_options(uf))


def validate_driver_form(data, *, is_create=False):
    errors = []
    data = normalize_driver_form(data)
    nome = str(data.get("nome", "")).strip()
    cpf = str(data.get("cpf", "")).strip()
    if not nome:
        errors.append(DRIVER_ERROR_MESSAGES["nome_obrigatorio"])
    if not cpf:
        errors.append(DRIVER_ERROR_MESSAGES["cpf_obrigatorio"])
    elif not CPF_RE.match(cpf):
        errors.append("CPF deve estar no formato 000.000.000-00.")
    telefone = str(data.get("telefone", "")).strip()
    if telefone and not PHONE_RE.match(telefone):
        errors.append("Telefone deve estar no formato (00) 0 0000-0000.")
    email = str(data.get("email", "")).strip()
    if email and not is_valid_email(email):
        errors.append("E-mail invalido.")
    nascimento = str(data.get("nascimento", "")).strip()
    if nascimento and not DATE_RE.match(nascimento):
        errors.append("Data de nascimento deve estar no formato DD/MM/AAAA.")
    cnh = str(data.get("cnh", "")).strip()
    if cnh and not cnh.isdigit():
        errors.append("CNH deve conter somente numeros.")
    categoria = str(data.get("categoria", "")).strip()
    if categoria and categoria not in CNH_CATEGORY_OPTIONS:
        errors.append("Categoria de CNH invalida.")
    validade_cnh = str(data.get("validade_cnh", "")).strip()
    if validade_cnh and not CNH_VALIDITY_RE.match(validade_cnh):
        errors.append("Validade da CNH deve estar no formato MM/AAAA.")
    frota = str(data.get("frota", "")).strip()
    if frota and frota not in FROTA_OPTIONS:
        errors.append("Status da frota invalido.")
    errors.extend(validate_location_fields(data))
    if not _valid_ibge_city(data):
        errors.append("Cidade selecionada nao pertence ao Estado informado pelo IBGE.")
    return errors


def map_service_error(code):
    return DRIVER_ERROR_MESSAGES.get(str(code or ""), str(code or "Erro ao processar solicitacao."))
