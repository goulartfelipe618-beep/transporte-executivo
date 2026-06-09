"""P2.4 — Correções finais de go-live (dados apenas, sem alterar APIs)."""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, ".")

from app.company_model import company_key, ensure_company_portal_structure, find_company_user, is_corporate_client
from app.master.services.driver_portal_service import get_portal_link
from app.portal_urls import company_portal_base, company_portal_link, driver_portal_base
from app.storage import load_state, save_state

PRODUCTION_BUSINESS = "https://business.transporteexecutivo.com"
PRODUCTION_DRIVER = "https://driver.transporteexecutivo.com"
RESERVATIONS_FIX = {"NX80EAC80A", "NX9G5WUTLP"}


def apply_fixes(app):
    changes = []

    os.environ["COMPANY_PORTAL_BASE_URL"] = PRODUCTION_BUSINESS
    os.environ["DRIVER_PORTAL_BASE_URL"] = PRODUCTION_DRIVER

    for index, client in enumerate(app.clients):
        if not is_corporate_client(client):
            continue
        before_link = client.get("portal_link")
        before_codigo = client.get("portal_codigo")
        updated = ensure_company_portal_structure(client, company_portal_base(), app.clients)
        app.clients[index] = updated
        changes.append(
            {
                "type": "company",
                "id": updated.get("id"),
                "portal_codigo": updated.get("portal_codigo"),
                "portal_link_before": before_link,
                "portal_link_after": updated.get("portal_link"),
                "canonical": company_portal_link(updated),
            }
        )

    for index, driver in enumerate(app.drivers):
        before = driver.get("portal_link") or driver.get("link")
        link = get_portal_link(driver)
        driver["portal_link"] = link
        driver["link"] = link
        app.drivers[index] = driver
        changes.append(
            {
                "type": "driver",
                "id": driver.get("id"),
                "portal_link_before": before,
                "portal_link_after": link,
            }
        )

    for reservation in app.reservations:
        numero = str(reservation.get("numero", ""))
        if numero not in RESERVATIONS_FIX:
            continue
        before_status = reservation.get("status")
        reservation["status"] = "Pendente"
        changes.append(
            {
                "type": "reservation",
                "numero": numero,
                "action": "status_pendente_sem_motorista_inequivoco",
                "status_before": before_status,
                "status_after": "Pendente",
                "driver_id": reservation.get("driver_id"),
            }
        )

    return changes


def audit_company_users(app):
    company = next((c for c in app.clients if is_corporate_client(c)), None)
    if not company:
        return {"error": "empresa_nao_encontrada"}
    users = []
    for user in company.get("usuarios") or []:
        senha = str(user.get("senha", ""))
        has_valid = senha.startswith("$2") or bool(user.get("password_hash"))
        users.append(
            {
                "id": user.get("id"),
                "email": user.get("email"),
                "perfil": user.get("perfil"),
                "status": user.get("status"),
                "has_valid_password_hash": has_valid,
                "must_change_password": user.get("must_change_password"),
            }
        )
    return {"company_id": company.get("id"), "users": users}


def main():
    state = load_state()
    app = SimpleNamespace(**state)
    for key in state:
        if not key.startswith("_"):
            setattr(app, key, state[key])

    print("=== AUDITORIA USUARIOS EMPRESA ===")
    print(json.dumps(audit_company_users(app), ensure_ascii=False, indent=2))

    print("\n=== APLICANDO CORRECOES ===")
    changes = apply_fixes(app)
    print(json.dumps(changes, ensure_ascii=False, indent=2))

    print("\n=== PERSISTINDO ===")
    save_state(app)
    print("save_state: OK")

    print("\n=== VALIDACAO LINKS ===")
    company = next(c for c in app.clients if is_corporate_client(c))
    driver = app.drivers[0] if app.drivers else {}
    print("empresa_link", company.get("portal_link"))
    print("empresa_canonical_ok", company.get("portal_link", "").startswith(f"{PRODUCTION_BUSINESS}/{company.get('id')}/"))
    print("motorista_link", driver.get("portal_link"))
    print("motorista_ok", str(driver.get("portal_link", "")).startswith(PRODUCTION_DRIVER))

    for numero in RESERVATIONS_FIX:
        row = next((r for r in app.reservations if r.get("numero") == numero), None)
        print(f"reserva_{numero}", row.get("status") if row else "missing")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
