"""Validadores extraidos de components.py — sem Tkinter."""
from __future__ import annotations

import re
from datetime import datetime

from app.domain.formatters import format_amount, parse_amount

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _digits_only(value):
    return re.sub(r"\D", "", str(value or ""))


def is_valid_email(value):
    return bool(EMAIL_PATTERN.match(str(value or "").strip()))


def validate_email_value(value, *, label="E-mail"):
    raw = str(value or "").strip()
    if not raw:
        return False, f"Informe: {label}."
    if not is_valid_email(raw):
        return False, f"{label} invalido. Use o formato nome@dominio.com"
    return True, ""


def parse_br_datetime(date_value, time_value=""):
    date_digits = _digits_only(date_value)
    if len(date_digits) != 8:
        return None
    time_digits = _digits_only(time_value)
    if len(time_digits) == 4:
        hour, minute = int(time_digits[0:2]), int(time_digits[2:4])
    else:
        hour, minute = 0, 0
    try:
        return datetime(
            int(date_digits[4:8]),
            int(date_digits[2:4]),
            int(date_digits[0:2]),
            hour,
            minute,
        )
    except ValueError:
        return None


def validate_future_datetime(date_value, time_value="", *, label="Data/hora"):
    parsed = parse_br_datetime(date_value, time_value)
    if not parsed:
        return False, f"{label} invalida. Use DD/MM/AAAA e HH:MM."
    if parsed < datetime.now():
        return False, f"{label} nao pode ser anterior a data e hora atuais."
    return True, ""


def calculate_total_amount(valor_base, desconto):
    base = parse_amount(valor_base)
    discount = parse_amount(desconto)
    discount = min(max(discount, 0), 100)
    return round(base * (1 - discount / 100), 2)
