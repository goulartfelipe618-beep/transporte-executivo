"""Portal motorista — links, ativacao e sessoes (sem alterar portal_server.py)."""
from __future__ import annotations

from app.driver_portal_access import activation_token_pending, reset_activation_state
from app.portal_auth import (
    USER_TYPE_DRIVER,
    activation_token_valid,
    driver_has_password,
    driver_reservations_for,
    ensure_driver_portal_slug,
    generate_activation_token,
)
from app.portal_urls import driver_portal_link


def portal_slug(driver):
    return ensure_driver_portal_slug(driver)


def get_portal_link(driver):
    slug = portal_slug(driver)
    return driver_portal_link(driver, slug=slug)


def portal_info(driver):
    activated = driver_has_password(driver)
    token = str(driver.get("activation_token", ""))
    expires = str(driver.get("activation_expires_at", ""))
    consumed_at = str(driver.get("activation_token_consumed_at", ""))
    activated_at = str(driver.get("portal_activated_at", ""))
    if activated:
        status_label = "Ativado"
        if activated_at:
            status_label = f"Ativado em {activated_at}"
    elif consumed_at:
        status_label = f"Token consumido em {consumed_at} — aguardando senha"
    elif token:
        status_label = "Pendente ativacao"
    else:
        status_label = "Sem token"
    return {
        "portal_ativo": bool(driver.get("portal_ativo")),
        "portal_activated": activated,
        "portal_slug": portal_slug(driver),
        "portal_link": get_portal_link(driver),
        "activation_token": token,
        "activation_expires_at": expires,
        "activation_token_consumed_at": consumed_at,
        "portal_activated_at": activated_at,
        "activation_pending": activation_token_pending(driver),
        "token_consumed": bool(consumed_at) and not activated,
        "portal_status_label": status_label,
    }


def refresh_activation_token(driver):
    reset_activation_state(driver)
    token = generate_activation_token(driver)
    driver["portal_ativo"] = False
    driver.pop("portal_activated_at", None)
    return token


def portal_last_access(app, driver):
    driver_id = str(driver.get("id", ""))
    slug = portal_slug(driver)
    latest = ""
    for session in getattr(app, "portal_sessions", []) or []:
        if session.get("user_type") != USER_TYPE_DRIVER:
            continue
        if str(session.get("user_id", "")) != driver_id and str(session.get("slug", "")) != slug:
            continue
        stamp = str(session.get("last_activity") or session.get("created_at") or "")
        if stamp and (not latest or stamp > latest):
            latest = stamp
    return latest


def driver_reservations(app, driver):
    return list(driver_reservations_for(app, driver))


def activation_valid(driver, token=None):
    token = token if token is not None else driver.get("activation_token")
    return activation_token_valid(driver, token)
