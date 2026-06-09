"""P3.1 — Validacao pos-deploy (local + URLs publicas)."""
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
from app.portal_server import driver_key, start_driver_portal_server
from app.storage import load_state
from app.version import APP_BUILD

PUBLIC = {
    "api": "https://api.transporteexecutivo.com",
    "sistema": "https://sistema.transporteexecutivo.com",
    "driver": "https://driver.transporteexecutivo.com",
    "business": "https://business.transporteexecutivo.com",
    "engine": "https://engine.transporteexecutivo.com",
}

REQUIRED_ENV = (
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "DRIVER_PORTAL_BASE_URL",
    "COMPANY_PORTAL_BASE_URL",
    "ENGINE_BASE_URL",
    "SISTEMA_WEB_BASE_URL",
    "INTEGRACAO_API_BASE_URL",
)


def _get(url, timeout=25):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "NexusP31-Validate/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def _post(url, payload, timeout=60):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def validate_public_urls(company):
    results = {}
    codigo = str(company.get("portal_codigo", "")).strip().upper()
    canonical = f"{PUBLIC['business']}/emp-000001/{codigo}" if codigo else ""

    checks = [
        ("health_api", f"{PUBLIC['api']}/api/v1/public/statistics"),
        ("health_sistema", f"{PUBLIC['sistema']}/api/deploy-info"),
        ("health_engine", f"{PUBLIC['engine']}/health"),
        ("driver_root", f"{PUBLIC['driver']}/"),
        ("business_root", f"{PUBLIC['business']}/"),
        ("business_legacy", f"{PUBLIC['business']}/empresa/nome-fantasia"),
    ]
    if canonical:
        checks.append(("business_canonical", canonical))

    for key, url in checks:
        try:
            code, body = _get(url)
            ok = code == 200 and len(body) > 50
            if key == "health_sistema":
                data = json.loads(body.decode("utf-8"))
                ok = ok and data.get("ok") and str(data.get("build", "")) >= "2026.09.09"
                results[key] = {"status": "APROVADO" if ok else "REPROVADO", "build": data.get("build")}
            else:
                results[key] = {"status": "APROVADO" if ok else "REPROVADO", "code": code}
        except Exception as exc:
            results[key] = {"status": "REPROVADO", "error": str(exc)[:120]}

    return results


def validate_local_homologation(password: str):
    state = load_state()
    app = SimpleNamespace(**state)
    app.save_state = lambda: None
    company = next(c for c in app.clients if c.get("id") == "emp-000001")
    user = find_company_user(company, company.get("email", ""))

    results = {}
    if not password or not verify_password(password, user.get("senha", "")):
        return {"login": "REPROVADO", "reason": "P31_COMPANY_PASSWORD ausente ou invalida"}

    app.company_portal_server = None
    cb = start_company_portal_server(app)
    slug = company_key(company)
    code, body = _post(f"{cb}/api/company/login", {"slug": slug, "email": user["email"], "password": password})
    token = body.get("token")
    results["company_login"] = "APROVADO" if token else "REPROVADO"
    if token:
        session = {"token": token, "slug": slug}
        for name, path, extra in (
            ("exportacao", "/api/company/export", {"format": "excel"}),
        ):
            code, payload = _post(f"{cb}{path}", {**session, **extra})
            results[name] = "APROVADO" if code == 200 and payload.get("ok") else "REPROVADO"

    app.driver_portal_server = None
    driver = app.drivers[0]
    cd = start_driver_portal_server(app)
    for pw in ("TestP2.1!", password):
        try:
            code, payload = _post(f"{cd}/api/driver/login", {"slug": driver_key(driver), "password": pw})
            if payload.get("token"):
                results["driver_login"] = "APROVADO"
                break
        except urllib.error.HTTPError:
            continue
    else:
        results["driver_login"] = "REPROVADO"

    from app.api_gateway import start_api_gateway_server
    from app.partner_network import ensure_partner_networks

    ensure_partner_networks(app)
    app.api_gateway_server = None
    gw = start_api_gateway_server(app)
    partner = app.partner_networks[0]
    code, payload = _post(
        f"{gw}/api/v1/network/{partner['slug']}/{partner['codigo']}/reserve",
        {
            "origem": "P31",
            "destino": "GRU",
            "data": "30/06/2026",
            "hora": "10:00",
            "nome": "P31",
            "telefone": "47999990000",
            "valor_total": 250,
            "source": "network",
            "flow": "express",
        },
        timeout=180,
    )
    results["network_reserve"] = "APROVADO" if code == 200 and payload.get("ok") else "REPROVADO"
    return results


def main():
    print(f"P31_BUILD_LOCAL={APP_BUILD}")
    missing_env = [key for key in REQUIRED_ENV if not os.environ.get(key, "").strip()]
    if missing_env:
        print("ENV_MISSING", missing_env)

    state = load_state()
    company = next(c for c in state.get("clients", []) if c.get("id") == "emp-000001")

    public = validate_public_urls(company)
    print("=== PUBLIC_URLS ===")
    print(json.dumps(public, ensure_ascii=False, indent=2))

    password = os.environ.get("P31_COMPANY_PASSWORD", "").strip()
    local = validate_local_homologation(password)
    print("=== LOCAL_HOMOLOGATION ===")
    print(json.dumps(local, ensure_ascii=False, indent=2))

    public_ok = all(v.get("status") == "APROVADO" for v in public.values())
    local_ok = all(v == "APROVADO" for k, v in local.items() if k not in {"reason"})
    print("PUBLIC_OK", public_ok)
    print("LOCAL_OK", local_ok)
    return 0 if public_ok and local_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
