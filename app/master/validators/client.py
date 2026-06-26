"""Validacao de clientes pessoa fisica."""
from __future__ import annotations

import re

from .input import validate_email_value


def validate_client_form(form_data, *, is_create=True):
    errors = []
    nome = str(form_data.get("nome", "")).strip()
    if not nome:
        errors.append("Informe o nome completo.")
    email = str(form_data.get("email", "")).strip()
    if email:
        ok, msg = validate_email_value(email, label="E-mail")
        if not ok:
            errors.append(msg)
    documento = re.sub(r"\D", "", str(form_data.get("documento", "")))
    if documento and len(documento) not in {11, 14}:
        errors.append("CPF deve ter 11 digitos.")
    return errors
