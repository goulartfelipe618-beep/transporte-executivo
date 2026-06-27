"""Localizacao estruturada para cadastros e mapa de abrangencia."""
from __future__ import annotations

from app import ibge
from app.company_model import is_corporate_client
from app.geocoding import geocode_address


def states_options():
    return ibge.get_states()


def city_options(uf):
    return ibge.get_municipalities(uf)


def district_options(city_id):
    districts = ibge.get_districts(city_id)
    if districts:
        return districts
    try:
        city_id = int(city_id or 0)
    except (TypeError, ValueError):
        city_id = 0
    return [{"id": city_id, "nome": "Centro", "municipio_id": city_id}] if city_id else []


def location_form_context(form=None):
    form = form or {}
    uf = str(form.get("estado_uf") or form.get("estado") or "").upper().strip()
    city_id = str(form.get("cidade_ibge_id") or "").strip()
    return {
        "location_states": states_options(),
        "location_cities": city_options(uf) if uf else [],
        "location_districts": district_options(city_id) if city_id else [],
    }


def validate_location_fields(data):
    errors = []
    if len(str(data.get("estado_uf") or data.get("estado") or "").strip()) != 2:
        errors.append("Selecione o Estado pela lista do IBGE.")
    try:
        city_id = int(data.get("cidade_ibge_id") or 0)
    except (TypeError, ValueError):
        city_id = 0
    if city_id <= 0:
        errors.append("Selecione a Cidade pela lista do IBGE.")
    if not str(data.get("bairro", "")).strip():
        errors.append("Selecione o Bairro/Regiao pela lista do IBGE.")
    if not str(data.get("logradouro", "")).strip():
        errors.append("Informe a rua.")
    if not str(data.get("numero", "")).strip():
        errors.append("Informe o numero.")
    return errors


def apply_location_payload(payload, form_data, *, existing=None):
    existing = existing or {}
    uf = str(form_data.get("estado_uf") or form_data.get("estado") or existing.get("estado_uf") or existing.get("estado") or "").upper().strip()
    city_id = _int_value(form_data.get("cidade_ibge_id") or existing.get("cidade_ibge_id"))
    city_name = str(form_data.get("cidade_nome") or existing.get("cidade_nome") or existing.get("cidade") or "").strip()
    if uf and city_id:
        for city in city_options(uf):
            if _int_value(city.get("id")) == city_id:
                city_name = city.get("nome", city_name)
                break
    state_name = ""
    for state in states_options():
        if state.get("sigla") == uf:
            state_name = state.get("nome", "")
            break

    bairro = str(form_data.get("bairro") or existing.get("bairro") or "").strip()
    logradouro = str(form_data.get("logradouro") or existing.get("logradouro") or "").strip()
    numero = str(form_data.get("numero") or existing.get("numero") or "").strip()
    complemento = str(form_data.get("complemento") or existing.get("complemento") or "").strip()
    endereco = compose_address(logradouro, numero, bairro, city_name, uf, complemento=complemento)

    payload.update(
        {
            "estado": uf,
            "estado_uf": uf,
            "estado_nome": state_name or existing.get("estado_nome", ""),
            "cidade": city_name,
            "cidade_nome": city_name,
            "cidade_ibge_id": city_id,
            "bairro": bairro,
            "logradouro": logradouro,
            "numero": numero,
            "complemento": complemento,
            "endereco": endereco,
        }
    )
    return payload


def compose_address(logradouro, numero, bairro, cidade, uf, *, complemento=""):
    rua = " ".join(str(logradouro or "").split())
    numero = str(numero or "").strip()
    bairro = str(bairro or "").strip()
    cidade = str(cidade or "").strip()
    uf = str(uf or "").strip().upper()
    complemento = str(complemento or "").strip()
    parts = []
    if rua:
        parts.append(f"{rua}, {numero}" if numero else rua)
    if complemento:
        parts.append(complemento)
    if bairro:
        parts.append(bairro)
    if cidade or uf:
        parts.append(f"{cidade} - {uf}".strip(" -"))
    return ", ".join(part for part in parts if part)


def build_coverage_entity_markers(runtime):
    markers = []
    for client in getattr(runtime, "clients", []) or []:
        kind = "empresa" if is_corporate_client(client) else "cliente_pf"
        name = (
            client.get("nome_fantasia")
            or client.get("razao_social")
            or client.get("nome")
            or client.get("nome_completo")
            or "Cliente"
        )
        _append_marker(markers, kind, name, client)
    for partner in getattr(runtime, "partner_networks", []) or []:
        name = partner.get("nome_rede") or partner.get("nome") or "Rede"
        _append_marker(markers, "rede", name, partner)
    return markers


def map_summary(markers):
    by_kind = {"cliente_pf": 0, "empresa": 0, "rede": 0}
    for marker in markers:
        by_kind[marker["kind"]] = by_kind.get(marker["kind"], 0) + 1
    return {
        "pins": len(markers),
        "clientes_pf": by_kind.get("cliente_pf", 0),
        "empresas": by_kind.get("empresa", 0),
        "redes": by_kind.get("rede", 0),
        "cidades": len({m.get("city") for m in markers if m.get("city")}),
    }


def _append_marker(markers, kind, name, record):
    address = structured_address(record)
    if not address:
        return
    lat, lng, source = geocode_address(address)
    if lat is None or lng is None:
        return
    markers.append(
        {
            "kind": kind,
            "name": str(name or "").strip(),
            "address": address,
            "city": str(record.get("cidade_nome") or record.get("cidade") or "").strip(),
            "lat": lat,
            "lng": lng,
            "source": source,
        }
    )


def structured_address(record):
    address = str(record.get("endereco") or "").strip()
    if address:
        return address
    return compose_address(
        record.get("logradouro"),
        record.get("numero"),
        record.get("bairro"),
        record.get("cidade_nome") or record.get("cidade"),
        record.get("estado_uf") or record.get("estado"),
        complemento=record.get("complemento", ""),
    )


def _int_value(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
