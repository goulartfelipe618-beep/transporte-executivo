"""E2E conjunto Motor ↔ Gateway — hotel-blumenau / 2C9HGU."""

import asyncio
import json
import sys

import httpx

GATEWAY = "http://127.0.0.1:8770"
MOTOR = "http://127.0.0.1:8000"
SLUG, CODIGO = "hotel-blumenau", "2C9HGU"


async def main() -> int:
    report: dict = {"steps": []}
    async with httpx.AsyncClient(timeout=60) as c:
        # Gateway direct
        cfg = (await c.get(f"{GATEWAY}/api/v1/network/{SLUG}/{CODIGO}")).json()
        report["gateway_config"] = {"ok": cfg.get("ok"), "nome": cfg.get("nome_rede"), "tipo": cfg.get("tipo_rede")}
        veh_g = (await c.get(f"{GATEWAY}/api/v1/network/{SLUG}/{CODIGO}/vehicles")).json()
        report["gateway_vehicles"] = {"total": veh_g.get("total"), "ids": [i.get("id") for i in veh_g.get("items", [])]}

        # Motor entry
        r1 = await c.get(f"{MOTOR}/{SLUG}/{CODIGO}")
        report["steps"].append({"step": "motor_entry", "status": r1.status_code})

        start_payload = {
            "trip_type": "one_way",
            "origin": "HOTEL BLUMENAU",
            "destination": "Aeroporto Navegantes",
            "trip_date": "2026-06-15",
            "trip_time": "10:00",
            "passenger_name": "E2E Conjunto",
            "passenger_whatsapp": "47988336609",
            "slug": SLUG,
            "codigo": CODIGO,
        }
        r2 = await c.post(f"{MOTOR}/api/v1/express/start", json=start_payload)
        start = r2.json()
        rid = start["reservation_id"]
        report["steps"].append({"step": "start", "status": r2.status_code, "reservation_id": rid})

        r3 = await c.get(f"{MOTOR}/api/v1/express/{rid}/vehicles")
        items = r3.json().get("items", [])
        report["steps"].append({"step": "motor_vehicles", "status": r3.status_code, "count": len(items), "vehicles": items})

        if not items:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 1

        v = items[0]
        sel = {
            "vehicle_id": v["id"],
            "category": v["category"],
            "name": v["name"],
            "passengers": v["passengers"],
            "luggage": v["luggage"],
            "price": v["price"],
        }
        await c.post(f"{MOTOR}/api/v1/express/{rid}/vehicle", json=sel)

        conf = await c.post(f"{MOTOR}/api/v1/express/{rid}/confirm", json={"lgpd_accepted": True})
        confirm = conf.json()
        report["steps"].append({
            "step": "confirm",
            "status": conf.status_code,
            "reservation_id": confirm.get("reservation_id"),
            "reservation_code": confirm.get("reservation_code"),
            "master_reservation_id": confirm.get("master_reservation_id"),
            "transport_request_id": confirm.get("transport_request_id"),
            "gateway_response": confirm.get("gateway_response"),
        })

    ok = (
        report["gateway_config"].get("ok")
        and report["gateway_vehicles"].get("total", 0) >= 1
        and report["steps"][-1].get("master_reservation_id")
    )
    report["E2E_OK"] = bool(ok)
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
