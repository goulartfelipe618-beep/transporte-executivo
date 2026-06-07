"""Motor de precificacao preparatorio baseado em parametros operacionais."""
from datetime import datetime

from .operational_network import LOCATION_MODE_MANUAL, location_display, resolve_location


def parse_money(value):
    raw = str(value or "").replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.0


def format_money(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _vehicle_category(vehicle):
    return str(vehicle.get("tipo_veiculo") or vehicle.get("categoria") or "Padrao").strip()


def list_pricing_sources(app, categoria=None):
    categoria = str(categoria or "").strip().lower()
    sources = []

    for vehicle in getattr(app, "vehicles", []):
        if str(vehicle.get("status", "Ativo")).lower() not in {"ativo", "operando"}:
            continue
        if str(vehicle.get("portal_publicado", True)).lower() in {"nao", "false", "0"}:
            continue
        vehicle_category = _vehicle_category(vehicle).lower()
        if categoria and categoria not in vehicle_category and vehicle_category not in categoria:
            continue
        valor_km = parse_money(vehicle.get("valor_km"))
        if valor_km <= 0:
            continue
        sources.append(
            {
                "tipo": "veiculo",
                "id": vehicle.get("id") or vehicle.get("placa") or vehicle.get("modelo", ""),
                "nome": f'{vehicle.get("marca", "")} {vehicle.get("modelo", "")}'.strip(),
                "categoria": _vehicle_category(vehicle),
                "valor_km": valor_km,
                "valor_hora": parse_money(vehicle.get("valor_hora")),
                "tarifa_base": parse_money(vehicle.get("tarifa_base")),
                "valor_minimo": parse_money(vehicle.get("valor_minimo")),
            }
        )

    for driver in getattr(app, "drivers", []):
        status = str(driver.get("status_operacional") or driver.get("frota") or "Ativo").lower()
        if status not in {"ativo", "homologado", "operando"}:
            continue
        valor_km = parse_money(driver.get("valor_km"))
        if valor_km <= 0:
            continue
        driver_category = str(driver.get("categoria_veiculo") or driver.get("categoria") or "Padrao").lower()
        if categoria and categoria not in driver_category and driver_category not in categoria:
            continue
        sources.append(
            {
                "tipo": "motorista",
                "id": driver.get("cpf") or driver.get("nome", ""),
                "nome": driver.get("nome", "Motorista"),
                "categoria": driver.get("categoria_veiculo") or driver.get("categoria") or "Padrao",
                "valor_km": valor_km,
                "valor_hora": parse_money(driver.get("valor_hora")),
                "tarifa_base": parse_money(driver.get("tarifa_base")),
                "valor_minimo": parse_money(driver.get("valor_minimo")),
            }
        )

    return sources


def resolve_route_endpoint(app, label, modo=None, point_id=None, manual=""):
    if isinstance(label, dict):
        return label
    return resolve_location(app, modo or LOCATION_MODE_MANUAL, point_id, label or manual)


def estimate_route(app, origem, destino, categoria, km=None, origem_modo=None, origem_point_id=None, destino_modo=None, destino_point_id=None):
    origem_resolved = resolve_route_endpoint(app, origem, origem_modo, origem_point_id)
    destino_resolved = resolve_route_endpoint(app, destino, destino_modo, destino_point_id)
    origem_label = location_display(origem_resolved)
    destino_label = location_display(destino_resolved)
    km_value = float(km or 0)
    sources = list_pricing_sources(app, categoria)
    options = []
    for source in sources:
        total = source["tarifa_base"] + (km_value * source["valor_km"])
        if source["valor_minimo"]:
            total = max(total, source["valor_minimo"])
        options.append(
            {
                **source,
                "origem": origem_label,
                "destino": destino_label,
                "origem_endereco": origem_resolved.get("endereco", origem_label),
                "destino_endereco": destino_resolved.get("endereco", destino_label),
                "origem_modo": origem_resolved.get("modo", LOCATION_MODE_MANUAL),
                "destino_modo": destino_resolved.get("modo", LOCATION_MODE_MANUAL),
                "distancia_km": km_value,
                "valor_estimado": round(total, 2),
                "valor_estimado_fmt": format_money(total),
                "calculado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
        )
    options.sort(key=lambda item: item["valor_estimado"])
    return {
        "origem": origem_label,
        "destino": destino_label,
        "origem_resolved": origem_resolved,
        "destino_resolved": destino_resolved,
        "categoria": categoria,
        "distancia_km": km_value,
        "distance_provider": "manual" if km_value else "pending_maps_api",
        "maps_ready": True,
        "options": options,
        "menor_valor": options[0]["valor_estimado_fmt"] if options else "",
        "maior_valor": options[-1]["valor_estimado_fmt"] if options else "",
    }


def published_vehicle_catalog(app):
    catalog = []
    for vehicle in getattr(app, "vehicles", []):
        if str(vehicle.get("status", "Ativo")).lower() not in {"ativo", "operando"}:
            continue
        if str(vehicle.get("portal_publicado", True)).lower() in {"nao", "false", "0"}:
            continue
        catalog.append(
            {
                "id": vehicle.get("id") or vehicle.get("placa", ""),
                "foto": vehicle.get("capa", ""),
                "categoria": _vehicle_category(vehicle),
                "capacidade": vehicle.get("capacidade", vehicle.get("passageiros", "")),
                "bagagens": vehicle.get("bagagens", ""),
                "aplicacao": vehicle.get("aplicacao", vehicle.get("tipo_veiculo", "")),
                "marca": vehicle.get("marca", ""),
                "modelo": vehicle.get("modelo", ""),
            }
        )
    return catalog
