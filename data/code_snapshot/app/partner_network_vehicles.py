"""Veiculos reais da rede — filtro por cidade/UF do parceiro (sem mocks)."""
from __future__ import annotations

import re
import unicodedata

from .company_model import is_corporate_client
from .operational_network import find_network_point
from .platform_contract import map_vehicle_to_public_vehicle

_ACTIVE_VEHICLE = {"ativo", "operando"}
_ACTIVE_DRIVER = {"ativo", "homologado", "operando"}
_ACTIVE_COMPANY = {"ativa", "ativo", "active"}
_INACTIVE_COMPANY = {"inativa", "bloqueada", "inativo", "bloqueado"}


def _token(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-zA-Z0-9]+", "", text).lower()


def _extract_uf(value):
    raw = str(value or "").strip().upper()
    match = re.search(r"\(([A-Z]{2})\)", raw)
    if match:
        return match.group(1)
    if len(raw) == 2 and raw.isalpha():
        return raw
    return raw[:2] if len(raw) >= 2 else raw


def _city_matches(left, right):
    a, b = _token(left), _token(right)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _uf_matches(left, right):
    a, b = _extract_uf(left), _extract_uf(right)
    if not a or not b:
        return True
    return a == b


def _location_matches(cidade, uf, partner_cidade, partner_uf):
    return _city_matches(cidade, partner_cidade) and _uf_matches(uf, partner_uf)


def _partner_location(partner):
    return str(partner.get("cidade", "")).strip(), str(partner.get("estado", "")).strip()


def _find_driver(app, driver_id):
    driver_id = str(driver_id or "").strip()
    if not driver_id:
        return None
    for driver in getattr(app, "drivers", []):
        if str(driver.get("id", "")) == driver_id or str(driver.get("cpf", "")) == driver_id:
            return driver
    return None


def _find_company(app, company_id):
    company_id = str(company_id or "").strip()
    if not company_id:
        return None
    for client in getattr(app, "clients", []):
        if str(client.get("id", "")) == company_id:
            return client
    return None


def _vehicle_location(vehicle, app):
    cidade = str(vehicle.get("cidade") or vehicle.get("cidade_nome") or "").strip()
    uf = str(vehicle.get("estado_uf") or vehicle.get("estado") or "").strip()
    driver = _find_driver(app, vehicle.get("driver_id") or vehicle.get("motorista_id"))
    if driver:
        cidade = cidade or str(driver.get("cidade", "")).strip()
        uf = uf or str(driver.get("estado", "")).strip()
    point = find_network_point(app, vehicle.get("operational_point_id") or vehicle.get("ponto_operacional_id"))
    if point:
        cidade = cidade or str(point.get("cidade_nome") or point.get("cidade", "")).strip()
        uf = uf or str(point.get("estado_uf") or point.get("estado", "")).strip()
    return cidade, uf


def _active_company_for_vehicle(app, vehicle, partner_cidade, partner_uf):
    linked = _find_company(app, vehicle.get("company_id") or vehicle.get("empresa_id"))
    if linked:
        if str(linked.get("status_empresa", linked.get("status", "Ativa"))).lower() in {"inativa", "bloqueada"}:
            return None
        company_city = str(linked.get("cidade", "")).strip()
        if company_city and not _city_matches(company_city, partner_cidade):
            return None
        return linked
    for client in getattr(app, "clients", []):
        if not is_corporate_client(client):
            continue
        if str(client.get("status_empresa", client.get("status", "Ativa"))).lower() in {"inativa", "bloqueada"}:
            continue
        company_city = str(client.get("cidade", "")).strip()
        if company_city and not _city_matches(company_city, partner_cidade):
            continue
        if not _uf_matches(client.get("estado", client.get("estado_uf", partner_uf)), partner_uf):
            continue
        return client
    if not getattr(app, "clients", []):
        return {"id": "platform", "nome": "Operador Master", "status_empresa": "Ativa"}
    return None


def _active_point_for_vehicle(app, vehicle, partner_cidade, partner_uf):
    linked = find_network_point(app, vehicle.get("operational_point_id") or vehicle.get("ponto_operacional_id"))
    if linked:
        if str(linked.get("status", "Operando")) != "Operando":
            return None
        city = str(linked.get("cidade_nome") or linked.get("cidade", "")).strip()
        uf = str(linked.get("estado_uf") or linked.get("estado", "")).strip()
        if not _location_matches(city, uf, partner_cidade, partner_uf):
            return None
        return linked
    for point in getattr(app, "operational_points", []):
        if str(point.get("status", "Operando")) != "Operando":
            continue
        if str(point.get("portal_publicado", True)).lower() in {"nao", "false", "0"}:
            continue
        city = str(point.get("cidade_nome") or point.get("cidade", "")).strip()
        uf = str(point.get("estado_uf") or point.get("estado", "")).strip()
        if _location_matches(city, uf, partner_cidade, partner_uf):
            return point
    return None


def _vehicle_eligible(app, vehicle, partner):
    if str(vehicle.get("status", "Ativo")).lower() not in _ACTIVE_VEHICLE:
        return False
    if str(vehicle.get("portal_publicado", True)).lower() in {"nao", "false", "0"}:
        return False
    partner_cidade, partner_uf = _partner_location(partner)
    if not partner_cidade:
        return False
    cidade, uf = _vehicle_location(vehicle, app)
    if not _location_matches(cidade, uf, partner_cidade, partner_uf):
        return False
    driver = _find_driver(app, vehicle.get("driver_id") or vehicle.get("motorista_id"))
    if not driver:
        return False
    status = str(driver.get("status_operacional") or driver.get("frota") or "Ativo").lower()
    if status not in _ACTIVE_DRIVER:
        return False
    driver_city = str(driver.get("cidade", "")).strip()
    driver_uf = str(driver.get("estado", "")).strip()
    if driver_city and not _city_matches(driver_city, partner_cidade):
        return False
    if driver_uf and not _uf_matches(driver_uf, partner_uf):
        return False
    if not _active_company_for_vehicle(app, vehicle, partner_cidade, partner_uf):
        return False
    if not _active_point_for_vehicle(app, vehicle, partner_cidade, partner_uf):
        return False
    return True


def network_vehicles_for_partner(app, partner):
    partner_cidade, partner_uf = _partner_location(partner)
    items = []
    for vehicle in getattr(app, "vehicles", []):
        if not isinstance(vehicle, dict) or not _vehicle_eligible(app, vehicle, partner):
            continue
        cidade, uf = _vehicle_location(vehicle, app)
        dto = map_vehicle_to_public_vehicle(vehicle)
        dto.update(
            {
                "cidade": cidade,
                "estado": _extract_uf(uf),
                "driver_id": vehicle.get("driver_id") or vehicle.get("motorista_id", ""),
                "operational_point_id": vehicle.get("operational_point_id") or vehicle.get("ponto_operacional_id", ""),
            }
        )
        items.append(dto)
    return {
        "cidade_rede": partner_cidade,
        "estado_rede": _extract_uf(partner_uf),
        "items": items,
        "total": len(items),
    }
