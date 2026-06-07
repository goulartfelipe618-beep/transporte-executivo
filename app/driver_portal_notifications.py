"""Notificacoes do Portal Motorista — persistencia JSON por motorista."""
from __future__ import annotations

from datetime import datetime

MAX_NOTIFICATIONS = 100


def ensure_notifications(driver):
    if "portal_notifications" not in driver or driver["portal_notifications"] is None:
        driver["portal_notifications"] = []
    if "portal_notified_reservas" not in driver:
        driver["portal_notified_reservas"] = []
    return driver["portal_notifications"]


def push_notification(driver, tipo, titulo, mensagem, *, referencia_id=""):
    items = ensure_notifications(driver)
    notice = {
        "id": f"ntf-{len(items) + 1:04d}",
        "tipo": tipo,
        "titulo": titulo,
        "mensagem": mensagem,
        "referencia_id": referencia_id,
        "lida": False,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    items.insert(0, notice)
    driver["portal_notifications"] = items[:MAX_NOTIFICATIONS]
    return notice


def sync_reservation_notifications(app, driver):
    from .portal_auth import driver_reservations_for

    notified = set(driver.get("portal_notified_reservas") or [])
    changed = False
    for reservation in driver_reservations_for(app, driver):
        numero = str(reservation.get("numero", ""))
        if not numero or numero in notified:
            continue
        status = str(reservation.get("status", "")).lower()
        if status in {"cancelada", "cancelado"}:
            push_notification(
                driver,
                "reserva_cancelada",
                "Reserva cancelada",
                f"Reserva {numero} foi cancelada.",
                referencia_id=numero,
            )
        else:
            push_notification(
                driver,
                "reserva_nova",
                "Nova reserva",
                f"Reserva {numero} atribuida a voce.",
                referencia_id=numero,
            )
        notified.add(numero)
        changed = True
    if changed:
        driver["portal_notified_reservas"] = list(notified)[-200:]
    return changed


def mark_notification_read(driver, notification_id):
    for item in ensure_notifications(driver):
        if str(item.get("id")) == str(notification_id):
            item["lida"] = True
            return True
    return False


def notifications_dto(driver):
    return [
        {
            "id": item.get("id"),
            "tipo": item.get("tipo"),
            "titulo": item.get("titulo"),
            "mensagem": item.get("mensagem"),
            "referencia_id": item.get("referencia_id"),
            "lida": bool(item.get("lida")),
            "criado_em": item.get("criado_em"),
        }
        for item in ensure_notifications(driver)
    ]
