"""Cliente Gateway Publico V1 para o Portal Empresa."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .platform_contract import (
    API_PUBLIC_LOCATIONS_AGGREGATE,
    API_PUBLIC_LOCATIONS_BASE,
    API_PUBLIC_STATISTICS,
    API_PUBLIC_VEHICLES,
    GATEWAY_PORT,
)

GATEWAY_BASE = os.environ.get("INTEGRACAO_API_BASE_URL", f"http://127.0.0.1:{GATEWAY_PORT}")


def _gateway_get(path, query=""):
    url = f"{GATEWAY_BASE.rstrip('/')}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=6) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_gateway_or_fallback(app, path, fallback_fn):
    try:
        payload = _gateway_get(path)
        if payload.get("ok") is not False:
            return payload, "gateway"
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        pass
    return fallback_fn(), "local"


def gateway_locations(app, *, type_filter="", state="", city=""):
    query_parts = []
    if type_filter:
        query_parts.append(f"type={type_filter}")
    if state:
        query_parts.append(f"state={state}")
    if city:
        query_parts.append(f"city={city}")
    query = "&".join(query_parts)
    path = API_PUBLIC_LOCATIONS_AGGREGATE + (f"?{query}" if query else "")

    def fallback():
        from .operational_network import active_network_points, ensure_operational_network

        ensure_operational_network(app)
        items = [
            {
                "nome": p.get("nome", ""),
                "tipo": p.get("tipo", ""),
                "cidade": p.get("cidade_nome", ""),
                "estado": p.get("estado_uf", ""),
            }
            for p in active_network_points(app, public_only=True)
        ]
        return {"ok": True, "items": items, "total": len(items)}

    return fetch_gateway_or_fallback(app, path, fallback)


def gateway_coverage(app):
    def fallback():
        from .platform_contract import build_coverage_summary

        summary = build_coverage_summary(app)
        return {
            "ok": True,
            "states": [{"uf": uf, "operational_points": count} for uf, count in _states_from_summary(summary).items()],
            "cities": [],
            "totals": {
                "states": summary.get("states_covered", 0),
                "cities": summary.get("cities_covered", 0),
                "operational_points": summary.get("operational_points_total", 0),
            },
        }

    path = API_PUBLIC_STATISTICS
    try:
        stats = _gateway_get("/api/v1/public/coverage")
        if stats.get("ok"):
            return stats, "gateway"
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        pass
    return fetch_gateway_or_fallback(app, path, fallback)


def _states_from_summary(summary):
    return {}


def gateway_airports(app):
    return fetch_gateway_or_fallback(app, f"{API_PUBLIC_LOCATIONS_BASE}/airports", lambda: {"ok": True, "items": [], "total": 0})


def gateway_hotels(app):
    return fetch_gateway_or_fallback(app, f"{API_PUBLIC_LOCATIONS_BASE}/hotels", lambda: {"ok": True, "items": [], "total": 0})


def gateway_vehicles(app):
    def fallback():
        from .pricing_engine import published_vehicle_catalog

        items = published_vehicle_catalog(app)
        return {"ok": True, "items": items, "total": len(items)}

    return fetch_gateway_or_fallback(app, API_PUBLIC_VEHICLES, fallback)
