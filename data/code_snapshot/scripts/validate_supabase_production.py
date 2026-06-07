"""Validacao producao: Supabase leitura/gravacao + gateway rede."""
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, ".")

from app.api_gateway import start_api_gateway_server
from app.partner_network import ensure_partner_networks
from app.partner_network_dtos import NETWORK_CONFIG_FIELDS
from app.repository import supabase_client as db
from app.repository.supabase_store import load_collection, save_collection
from app.storage import load_state, save_state


def _print_section(title):
    print(f"\n=== {title} ===")


def validate_reads():
    _print_section("LEITURA SUPABASE")
    tables = {
        "vehicles": "vehicles",
        "partner_networks": "partner_networks",
        "reservations": "reservations",
        "transport_requests": "transport_requests",
        "companies": "companies",
        "drivers": "drivers",
        "clients": "clients",
    }
    evidence = {}
    for label, key in tables.items():
        items = load_collection("clients") if key == "clients" else load_collection(key)
        sample_id = str((items[0].get("uuid") or items[0].get("id") or "")) if items else ""
        evidence[label] = {"count": len(items), "sample_id": sample_id}
        print(f"{label}: count={len(items)} sample_id={sample_id}")
    return evidence


def validate_writes():
    _print_section("GRAVACAO SUPABASE")
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    audit_item = {
        "id": f"aud-val-{stamp}",
        "action": "production.validation",
        "actor_type": "system",
        "actor_id": "validate_script",
        "payload": {"stamp": stamp},
    }
    save_collection("audit_log", [audit_item])
    audits = load_collection("audit_log")
    audit_match = next((a for a in audits if a.get("id") == audit_item["id"]), None)
    audit_uuid = (audit_match or {}).get("uuid", "")
    print(f"audit_log: legacy={audit_item['id']} uuid={audit_uuid}")

    partners = load_collection("partner_networks")
    partner = next((p for p in partners if p.get("slug") == "hotel-blumenau"), partners[0] if partners else None)
    if not partner:
        return {"audit_log": audit_uuid}

    commission_item = {
        "id": f"netcom-val-{stamp}",
        "partner_id": partner.get("id"),
        "reservation_numero": f"VAL-{stamp}",
        "valor_base": 100.0,
        "percentual": 10.0,
        "valor_bruto": 100.0,
        "valor_comissao": 10.0,
        "status_pagamento": "pendente",
    }
    save_collection("network_commissions", [commission_item])
    commissions = load_collection("network_commissions")
    com_match = next((c for c in commissions if c.get("id") == commission_item["id"]), None)
    com_uuid = (com_match or {}).get("uuid", "")
    print(f"network_commissions: legacy={commission_item['id']} uuid={com_uuid}")
    return {"audit_log": audit_uuid, "network_commissions": com_uuid}


def validate_gateway():
    _print_section("GATEWAY REDE")
    state = load_state()
    app = SimpleNamespace(**state)
    app.save_state = lambda: save_state(app)
    ensure_partner_networks(app)
    url = start_api_gateway_server(app)
    if not url:
        print("FAIL gateway nao iniciou")
        return False

    with urllib.request.urlopen(f"{url}/api/v1/network/hotel-blumenau/2C9HGU", timeout=20) as resp:
        config = json.loads(resp.read().decode("utf-8"))
    missing = set(NETWORK_CONFIG_FIELDS) - set(config.keys())
    if missing or not config.get("ok"):
        print("FAIL GET config", missing, config)
        return False
    print(f"GET config ok slug={config.get('slug')} codigo={config.get('codigo')}")

    with urllib.request.urlopen(f"{url}/api/v1/network/hotel-blumenau/2C9HGU/vehicles", timeout=20) as resp:
        vehicles = json.loads(resp.read().decode("utf-8"))
    items = vehicles.get("items") or []
    if not vehicles.get("ok"):
        print("FAIL GET vehicles", vehicles)
        return False
    print(f"GET vehicles ok count={len(items)}")

    payload = {
        "origem": "Hotel Blumenau",
        "destino": "GRU",
        "data": "08/06/2026",
        "hora": "11:00",
        "nome": "Producao Validate",
        "telefone": "47988880099",
        "valor_total": 400.0,
        "source": "network",
        "flow": "express",
    }
    req = urllib.request.Request(
        f"{url}/api/v1/network/hotel-blumenau/2C9HGU/reserve",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print("FAIL POST reserve", exc.code, exc.read().decode())
        return False

    if not body.get("ok"):
        print("FAIL POST reserve body", body)
        return False
    print(
        "POST reserve ok",
        f"reservation_id={body.get('reservation_id')}",
        f"transport_request_id={body.get('transport_request_id')}",
    )
    return True


def main():
    if not db.is_configured():
        print("FAIL Supabase nao configurado")
        return 1
    reads = validate_reads()
    writes = validate_writes()
    gateway_ok = validate_gateway()
    print("\n=== RESUMO ===")
    print(json.dumps({"reads": reads, "writes": writes, "gateway_ok": gateway_ok}, ensure_ascii=False, indent=2))
    return 0 if gateway_ok and writes.get("audit_log") else 1


if __name__ == "__main__":
    raise SystemExit(main())
