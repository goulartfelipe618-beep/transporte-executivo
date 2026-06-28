"""Primeiro acesso ao portal motorista — token de uso unico."""
from __future__ import annotations

import re
from datetime import datetime

from .portal_auth import (
    activation_token_valid,
    clear_activation_token,
    driver_has_password,
)


def normalize_cpf(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def driver_cpf_matches(driver, cpf_input) -> bool:
    driver_cpf = normalize_cpf((driver or {}).get("cpf", ""))
    input_cpf = normalize_cpf(cpf_input)
    if not driver_cpf:
        return True
    if not input_cpf:
        return False
    return driver_cpf == input_cpf


def activation_token_pending(driver) -> bool:
    if not driver or driver_has_password(driver):
        return False
    if driver.get("activation_token_consumed_at"):
        return False
    return bool(str(driver.get("activation_token", "")).strip())


def activation_consumed_pending_password(driver) -> bool:
    if not driver or driver_has_password(driver):
        return False
    return bool(str(driver.get("activation_token_consumed_at", "")).strip())


def mark_activation_token_consumed(driver) -> None:
    driver["activation_token_consumed_at"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    clear_activation_token(driver)


def try_consume_activation_token(driver, token) -> bool:
    if not activation_token_pending(driver):
        return False
    if not activation_token_valid(driver, token):
        return False
    mark_activation_token_consumed(driver)
    return True


def reset_activation_state(driver) -> None:
    driver.pop("activation_token_consumed_at", None)
