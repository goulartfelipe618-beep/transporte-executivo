"""Auditoria E2E: GET config + GET vehicles + POST reserve."""
import json
import sys
import urllib.error
import urllib.request
from types import SimpleNamespace

sys.path.insert(0, ".")

from app.api_gateway import start_api_gateway_server
from app.partner_network import ensure_partner_networks
from app.partner_network_dtos import NETWORK_CONFIG_FIELDS
from app.storage import load_state, save_state


def main():
    state = load_state()
    app = SimpleNamespace(**state)
    app.save_state = lambda: save_state(app)
    ensure_partner_networks(app)
    url = start_api_gateway_server(app)
    if not url:
        print("FAIL gateway")
        return 1

    with urllib.request.urlopen(f"{url}/api/v1/network/hotel-blumenau/2C9HGU", timeout=15) as resp:
        config = json.loads(resp.read().decode("utf-8"))
    missing = set(NETWORK_CONFIG_FIELDS) - set(config.keys())
    if missing or not config.get("ok"):
        print("FAIL GET", missing)
        return 1

    with urllib.request.urlopen(f"{url}/api/v1/network/hotel-blumenau/2C9HGU/vehicles", timeout=15) as resp:
        vehicles = json.loads(resp.read().decode("utf-8"))
    if not vehicles.get("ok"):
        print("FAIL vehicles")
        return 1

    payload = {
        "origem": "Hotel Blumenau", "destino": "GRU", "data": "08/06/2026", "hora": "11:00",
        "nome": "Restore Test", "telefone": "47988880002", "valor_total": 400.0,
        "source": "network", "flow": "express",
    }
    req = urllib.request.Request(
        f"{url}/api/v1/network/hotel-blumenau/2C9HGU/reserve",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print("POST_FAIL", exc.code, exc.read().decode())
        return 1

    checks = {
        "reservation": any(r.get("id") == body.get("reservation_id") for r in app.reservations),
        "transport_request": any(t.get("id") == body.get("transport_request_id") for t in app.transport_requests),
        "audit_log": any(a.get("action") == "network.reservation.created" for a in app.audit_log),
    }
    print("E2E_OK", checks)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
