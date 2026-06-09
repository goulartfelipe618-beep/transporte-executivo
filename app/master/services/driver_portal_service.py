"""Portal motorista — links, ativacao e sessoes (sem alterar portal_server.py)."""
from __future__ import annotations

from app.portal_auth import (
    USER_TYPE_DRIVER,
    activation_token_valid,
    driver_has_password,
    driver_reservations_for,
    generate_activation_token,
)
from app.portal_server import driver_key
from app.portal_urls import driver_portal_link


def portal_slug(driver):
    return driver_key(driver)


def get_portal_link(driver):
    slug = portal_slug(driver)
    return driver_portal_link(driver, slug=slug)


def portal_info(driver):
    activated = driver_has_password(driver)
    token = str(driver.get("activation_token", ""))
    expires = str(driver.get("activation_expires_at", ""))
    return {
        "portal_ativo": bool(driver.get("portal_ativo")),
        "portal_activated": activated,
        "portal_slug": portal_slug(driver),
        "portal_link": get_portal_link(driver),
        "activation_token": token,
        "activation_expires_at": expires,
        "activation_pending": bool(token) and not activated,
        "portal_status_label": "Ativado" if activated else ("Pendente ativacao" if token else "Sem token"),
    }


def refresh_activation_token(driver):
    token = generate_activation_token(driver)
    driver["portal_ativo"] = False
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
