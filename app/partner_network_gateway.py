"""Rotas GET/POST /api/v1/network/* no Gateway (8770)."""
from __future__ import annotations

import json
from urllib.parse import unquote

from .partner_network import ensure_partner_networks, find_contributor, find_partner
from .partner_network_dtos import build_network_api_response
from .partner_network_reservations import register_network_reservation
from .partner_network_vehicles import network_vehicles_for_partner
from .platform_contract import (
    API_INBOUND_NETWORK_RESERVATION,
    API_NETWORK_BASE,
    CONTRACT_VERSION,
    ENTITY_RESERVATION,
    EVENT_RESERVATION_CREATED,
)
from .pricing_engine import estimate_route


def _parse_network_path(path):
    prefix = API_NETWORK_BASE + "/"
    if not path.startswith(prefix):
        return None
    rest = unquote(path[len(prefix) :]).strip("/")
    if not rest:
        return None
    parts = [p for p in rest.split("/") if p]
    if len(parts) < 2:
        return None
    slug, codigo = parts[0].lower(), parts[1].upper()
    action = parts[2].lower() if len(parts) > 2 else ""
    return slug, codigo, action


def _ref(query):
    values = query.get("ref") or query.get("contributor_ref") or []
    return str(values[0]).strip() if values else ""


def _load_partner(app, slug, codigo):
    ensure_partner_networks(app)
    partner = find_partner(app, slug=slug, codigo=codigo)
    if not partner:
        return None, 404, {"ok": False, "error": "partner_not_found"}
    if not partner.get("ativo", True) or str(partner.get("status", "")).lower() == "inativo":
        return None, 403, {"ok": False, "error": "partner_inactive"}
    return partner, None, None


def handle_network_get(app, path, query):
    parsed = _parse_network_path(path)
    if not parsed:
        return None
    slug, codigo, action = parsed
    partner, err_code, err_payload = _load_partner(app, slug, codigo)
    if err_code:
        return err_code, err_payload

    ref = _ref(query)
    contributor = find_contributor(partner, ref) if ref else None

    if action == "vehicles":
        catalog = network_vehicles_for_partner(app, partner)
        return 200, {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "partner_id": partner.get("id", ""),
            "cidade_rede": catalog["cidade_rede"],
            "estado_rede": catalog["estado_rede"],
            "items": catalog["items"],
            "total": catalog["total"],
        }

    dto = build_network_api_response(partner, contributor)
    dto["ok"] = True
    return 200, dto


def _body_json(raw):
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def _emit_reservation_webhook(app, result):
    if not result or not result.get("ok"):
        return
    try:
        from .api_gateway import notify_website
    except ImportError:
        return
    notify_website(
        app,
        EVENT_RESERVATION_CREATED,
        ENTITY_RESERVATION,
        result.get("reservation_id", ""),
        {
            "reservation_id": result.get("reservation_id"),
            "reservation_numero": result.get("reservation_numero"),
            "reservation_code": result.get("reservation_code"),
            "partner_id": result.get("partner_id"),
            "source": "network",
        },
    )


def handle_network_post(app, path, raw, query):
    if path == API_INBOUND_NETWORK_RESERVATION:
        try:
            result = register_network_reservation(app, _body_json(raw))
            _emit_reservation_webhook(app, result)
            return 200, result
        except ValueError as exc:
            return 400, {"ok": False, "error": str(exc)}
        except json.JSONDecodeError:
            return 400, {"ok": False, "error": "invalid_payload"}

    parsed = _parse_network_path(path)
    if not parsed:
        return None
    slug, codigo, action = parsed
    partner, err_code, err_payload = _load_partner(app, slug, codigo)
    if err_code:
        return err_code, err_payload

    try:
        payload = _body_json(raw)
    except json.JSONDecodeError:
        return 400, {"ok": False, "error": "invalid_payload"}

    ref = str(payload.get("ref") or payload.get("contributor_ref") or _ref(query) or "").strip()
    payload.setdefault("partner_slug", slug)
    payload.setdefault("partner_code", codigo)
    payload.setdefault("contributor_ref", ref)
    payload.setdefault("source", "network")
    payload.setdefault("flow", "express")

    if action == "quote":
        km = float(payload.get("distancia_km") or payload.get("km") or 25)
        quote = estimate_route(
            app,
            payload.get("origem") or partner.get("nome_rede", ""),
            payload.get("destino", ""),
            payload.get("categoria", ""),
            km=km,
        )
        options = quote.get("options") or []
        valor = options[0]["valor_estimado"] if options else 0
        return 200, {
            "ok": True,
            "valor_estimado": valor,
            "valor_estimado_fmt": options[0]["valor_estimado_fmt"] if options else "",
            "quote": quote,
        }

    if action == "reserve":
        try:
            result = register_network_reservation(app, payload)
            _emit_reservation_webhook(app, result)
            return 200, result
        except ValueError as exc:
            return 400, {"ok": False, "error": str(exc)}

    return 404, {"ok": False, "error": "not_found"}
