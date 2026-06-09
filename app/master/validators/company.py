"""Validadores do modulo Empresas — sem Tkinter."""
from __future__ import annotations

import re

from .input import is_valid_email

COMPANY_ERROR_MESSAGES = {
    "email_obrigatorio": "Informe o e-mail do usuario.",
    "email_duplicado": "E-mail ja cadastrado nesta empresa.",
    "usuario_nao_encontrado": "Usuario nao encontrado.",
    "nao_pode_excluir_a_si_mesmo": "Nao e possivel remover o proprio usuario.",
    "empresa_nao_encontrada": "Empresa nao encontrada.",
    "cnpj_obrigatorio": "Informe o CNPJ da empresa.",
    "razao_social_obrigatoria": "Informe a razao social.",
    "senha_obrigatoria": "Informe a senha inicial do usuario.",
}


def validate_company_form(data, *, is_create=False):
    errors = []
    razao = str(data.get("razao_social", "")).strip()
    cnpj = str(data.get("cnpj", "")).strip()
    if not razao:
        errors.append(COMPANY_ERROR_MESSAGES["razao_social_obrigatoria"])
    if not cnpj:
        errors.append(COMPANY_ERROR_MESSAGES["cnpj_obrigatorio"])
    email = str(data.get("email", "")).strip()
    if email and not is_valid_email(email):
        errors.append("E-mail corporativo invalido.")
    return errors


def validate_company_user_form(data, *, is_create=False):
    errors = []
    nome = str(data.get("nome", "")).strip()
    email = str(data.get("email", "")).strip()
    senha = str(data.get("senha", "")).strip()
    if not nome:
        errors.append("Informe o nome do usuario.")
    if not email:
        errors.append(COMPANY_ERROR_MESSAGES["email_obrigatorio"])
    elif not is_valid_email(email):
        errors.append("E-mail invalido.")
    if is_create and not senha:
        errors.append(COMPANY_ERROR_MESSAGES["senha_obrigatoria"])
    perfil = str(data.get("perfil", "")).strip()
    status = str(data.get("status", "")).strip()
    if not perfil:
        errors.append("Selecione o perfil.")
    if not status:
        errors.append("Selecione o status.")
    return errors


def map_service_error(code):
    return COMPANY_ERROR_MESSAGES.get(str(code or ""), str(code or "Erro ao processar solicitacao."))
