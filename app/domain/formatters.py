"""Formatadores monetarios compartilhados — fonte unica de parse/display BR."""
from __future__ import annotations


def parse_money_value(value):
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "0").replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_amount(value):
    return parse_money_value(value)


def money_display(value):
    amount = float(value or 0)
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_amount(value):
    return money_display(value)
