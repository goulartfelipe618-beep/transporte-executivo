"""P2.5 — Homologacao completa Portal Empresa pos-reset de senha."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from types import SimpleNamespace

sys.path.insert(0, ".")

from app.company_model import company_key, find_company_user
from app.company_portal import start_company_portal_server
from app.portal_auth import verify_password
from app.storage import load_state


def _post(url, payload, timeout=120):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main():
    password = os.environ.get("P25_COMPANY_PASSWORD", "").strip()
    if not password:
        print("MISSING_P25_COMPANY_PASSWORD")
        return 1

    state = load_state()
    app = SimpleNamespace(**state)
    app.save_state = lambda: None
    company = next(c for c in app.clients if c.get("id") == "emp-000001")
    slug = company_key(company)
    user = find_company_user(company, "felipe.goulart06@hotmail.com")
    if not verify_password(password, user.get("senha", "")):
        print("PASSWORD_VERIFY_FAIL")
        return 1

    app.company_portal_server = None
    base = start_company_portal_server(app)
    code, body = _post(f"{base}/api/company/login", {"slug": slug, "email": user["email"], "password": password})
    token = body.get("token")
    results = {"login": "APROVADO" if code == 200 and token else "REPROVADO"}
    if not token:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    session = {"token": token, "slug": slug}
    checks = (
        ("dashboard", "/api/company/dashboard", {}),
        ("passageiros", "/api/company/passengers/list", {}),
        ("centros_custo", "/api/company/cost-centers/list", {}),
        ("solicitacao", "/api/company/request", {
            "origem": "Origem P25",
            "destino": "Destino P25",
            "data": "25/06/2026",
            "hora": "09:00",
            "passageiro_nome": "Homolog P25",
        }),
        ("aprovacao", "/api/company/approvals/list", {}),
        ("financeiro", "/api/company/finance", {}),
        ("exportacao", "/api/company/export", {"format": "excel"}),
        ("logout", "/api/company/logout", {}),
    )
    for key, path, extra in checks:
        try:
            c, b = _post(f"{base}{path}", {**session, **extra})
            results[key] = "APROVADO" if c == 200 and b.get("ok") else "REPROVADO"
        except Exception:
            results[key] = "REPROVADO"

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(v == "APROVADO" for v in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
