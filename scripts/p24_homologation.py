"""P2.4 homologacao final pos-correcoes."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from types import SimpleNamespace

sys.path.insert(0, ".")

from app.api_gateway import start_api_gateway_server
from app.company_model import company_key, find_company_user
from app.company_portal import start_company_portal_server
from app.partner_network import ensure_partner_networks
from app.portal_auth import verify_password
from app.portal_server import driver_key, start_driver_portal_server
from app.storage import load_state


def _post(url, payload, timeout=120):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main():
    state = load_state()
    app = SimpleNamespace(**state)
    app.save_state = lambda: None
    results = {}

    company = next(c for c in app.clients if c.get("tipo_pessoa") == "juridica")
    slug = company_key(company)
    user = find_company_user(company, company.get("email", ""))
    known_pw = None
    if user:
        for pw in ("P22Homolog!", "TestP2.1!", "123456", "Admin@123", "Nexus2026!", "Transporte1!", "Felipe@123"):
            if verify_password(pw, user.get("senha", "")):
                known_pw = pw
                break

    app.company_portal_server = None
    cb = start_company_portal_server(app)
    token = None
    if known_pw:
        try:
            code, body = _post(f"{cb}/api/company/login", {"slug": slug, "email": user["email"], "password": known_pw})
            token = body.get("token")
            results["company_login"] = "APROVADO" if code == 200 and body.get("ok") else "REPROVADO"
        except urllib.error.HTTPError:
            results["company_login"] = "REPROVADO"
    else:
        results["company_login"] = "REPROVADO"

    session = {"token": token, "slug": slug} if token else {}
    for key, path, extra in (
        ("company_dashboard", "/api/company/dashboard", {}),
        ("company_finance", "/api/company/finance", {}),
        ("company_export", "/api/company/export", {"format": "excel"}),
    ):
        if not token:
            results[key] = "REPROVADO"
            continue
        try:
            code, body = _post(f"{cb}{path}", {**session, **extra})
            results[key] = "APROVADO" if code == 200 and body.get("ok") else "REPROVADO"
        except Exception:
            results[key] = "REPROVADO"

    app.driver_portal_server = None
    driver = app.drivers[0]
    slug_d = driver_key(driver)
    cd = start_driver_portal_server(app)
    try:
        code, body = _post(f"{cd}/api/driver/login", {"slug": slug_d, "password": "TestP2.1!"})
        dt = body.get("token")
        results["driver_login"] = "APROVADO" if dt else "REPROVADO"
        if dt:
            for key, path, extra in (
                ("driver_agenda", "/api/driver/reservations", {}),
                ("driver_status", "/api/driver/status", {"numero": "#1019", "status": "Em deslocamento"}),
            ):
                try:
                    code, body = _post(f"{cd}{path}", {"token": dt, **extra})
                    results[key] = "APROVADO" if code == 200 and body.get("ok") else "REPROVADO"
                except Exception:
                    results[key] = "REPROVADO"
        else:
            results["driver_agenda"] = "REPROVADO"
            results["driver_status"] = "REPROVADO"
    except Exception:
        results["driver_login"] = "REPROVADO"
        results["driver_agenda"] = "REPROVADO"
        results["driver_status"] = "REPROVADO"

    ensure_partner_networks(app)
    app.api_gateway_server = None
    gw = start_api_gateway_server(app)
    partner = app.partner_networks[0]
    reserve_payload = {
        "origem": "Hotel",
        "destino": "GRU",
        "data": "20/06/2026",
        "hora": "12:00",
        "nome": "P24",
        "telefone": "47999999999",
        "valor_total": 300,
        "source": "network",
        "flow": "express",
    }
    try:
        code, body = _post(
            f"{gw}/api/v1/network/{partner['slug']}/{partner['codigo']}/reserve",
            reserve_payload,
            timeout=180,
        )
        results["network_reserve"] = "APROVADO" if code == 200 and body.get("ok") else "REPROVADO"
        rid = body.get("reservation_id")
        has_com = any(c.get("reservation_id") == rid for c in app.network_commissions)
        results["network_commission"] = "APROVADO" if has_com else "REPROVADO"
    except Exception:
        results["network_reserve"] = "REPROVADO"
        results["network_commission"] = "REPROVADO"

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(v == "APROVADO" for v in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
