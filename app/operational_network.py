"""Rede Operacional unificada — pontos utilizados em toda a plataforma."""
import re
import unicodedata
from datetime import datetime

from .geography import normalize_operational_point, operational_point_label

NETWORK_TYPES = [
    "Aeroporto",
    "Hotel",
    "Centro de eventos",
    "Centro de convencoes",
    "Hub operacional",
    "Parceiro corporativo",
    "Ponto de apoio",
]

LEGACY_TYPE_MAP = {
    "Centro de eventos": "Centro de eventos",
    "Regiao atendida": "Hub operacional",
    "Hub operacional": "Hub operacional",
    "Hotel": "Hotel",
    "Aeroporto": "Aeroporto",
    "Operador": "Parceiro corporativo",
    "Parceiro Corporativo": "Parceiro corporativo",
    "Centro de Eventos": "Centro de eventos",
}

LOCATION_MODE_MANUAL = "manual"
LOCATION_MODE_NETWORK = "rede"

WEBSITE_TYPE_PREFIX = {
    "Aeroporto": "aeroporto",
    "Hotel": "hotel",
    "Centro de eventos": "centro-de-eventos",
    "Centro de convencoes": "centro-de-convencoes",
    "Hub operacional": "hub",
    "Parceiro corporativo": "parceiro",
    "Ponto de apoio": "ponto-de-apoio",
}


def slugify(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "local"


def website_slug(point):
    existing = str(point.get("website_slug") or "").strip()
    if existing:
        return existing
    prefix = WEBSITE_TYPE_PREFIX.get(point.get("tipo"), "local")
    city = slugify(point.get("cidade_nome") or point.get("cidade", ""))
    name = slugify(point.get("nome", ""))
    parts = [prefix, name]
    if city:
        parts.append(city)
    return "-".join(part for part in parts if part)


def enrich_operational_point(record):
    point = normalize_operational_point(record)
    tipo = LEGACY_TYPE_MAP.get(point.get("tipo"), point.get("tipo"))
    if tipo not in NETWORK_TYPES:
        tipo = "Hub operacional"
    point["tipo"] = tipo
    point["website_slug"] = website_slug(point)
    point["website_path"] = f"/{point['website_slug']}"
    point["portal_publicado"] = bool(record.get("portal_publicado", True))
    point["contato"] = str(record.get("contato", "")).strip()
    point["legacy_source"] = str(record.get("legacy_source", "")).strip()
    point["legacy_source_id"] = str(record.get("legacy_source_id", "")).strip()
    return point


def ensure_operational_network(app):
    if not hasattr(app, "operational_points"):
        app.operational_points = []
    migrated, changed = migrate_catalog_sources(app)
    points = [enrich_operational_point(item) for item in app.operational_points]
    app.operational_points = points
    return points, migrated or changed


def active_network_points(app, public_only=False):
    ensure_operational_network(app)
    points = []
    for point in app.operational_points:
        if point.get("status") != "Operando":
            continue
        if public_only and not point.get("portal_publicado", True):
            continue
        points.append(point)
    return points


def find_network_point(app, point_id):
    if not point_id:
        return None
    for point in getattr(app, "operational_points", []):
        if str(point.get("id")) == str(point_id):
            return point
    return None


def network_point_options(app, public_only=False):
    return [
        {
            "id": point.get("id"),
            "label": operational_point_label(point),
            "nome": point.get("nome", ""),
            "tipo": point.get("tipo", ""),
            "cidade": point.get("cidade_nome", ""),
            "estado": point.get("estado_uf", ""),
            "endereco": point.get("endereco", ""),
            "website_path": point.get("website_path", ""),
        }
        for point in active_network_points(app, public_only=public_only)
    ]


def grouped_locations(app, public_only=False):
    grouped = {tipo: [] for tipo in NETWORK_TYPES}
    for point in active_network_points(app, public_only=public_only):
        grouped.setdefault(point.get("tipo", "Hub operacional"), []).append(
            {
                "id": point.get("id"),
                "nome": point.get("nome", ""),
                "tipo": point.get("tipo", ""),
                "cidade": point.get("cidade_nome", ""),
                "estado": point.get("estado_uf", ""),
                "endereco": point.get("endereco", ""),
                "website_path": point.get("website_path", ""),
            }
        )
    return grouped


def resolve_location(app, modo, point_id, manual_text):
    manual_text = str(manual_text or "").strip()
    if str(modo or "").lower() == LOCATION_MODE_NETWORK and point_id:
        point = find_network_point(app, point_id)
        if point:
            return {
                "modo": LOCATION_MODE_NETWORK,
                "point_id": point.get("id", ""),
                "display": point.get("nome", ""),
                "nome": point.get("nome", ""),
                "tipo": point.get("tipo", ""),
                "cidade": point.get("cidade_nome", ""),
                "estado": point.get("estado_uf", ""),
                "endereco": point.get("endereco", ""),
                "website_path": point.get("website_path", ""),
            }
    return {
        "modo": LOCATION_MODE_MANUAL,
        "point_id": "",
        "display": manual_text,
        "nome": manual_text,
        "tipo": "",
        "cidade": "",
        "estado": "",
        "endereco": manual_text,
        "website_path": "",
    }


def location_display(location):
    location = location or {}
    if location.get("modo") == LOCATION_MODE_NETWORK:
        parts = [location.get("nome", ""), location.get("cidade", ""), location.get("estado", "")]
        return " / ".join(part for part in parts if part)
    return location.get("display") or location.get("endereco") or ""


def migrate_catalog_sources(app):
    changed = False
    existing_ids = {str(item.get("legacy_source_id")) for item in getattr(app, "operational_points", []) if item.get("legacy_source_id")}
    points = list(getattr(app, "operational_points", []))

    for source_key, tipo, legacy_prefix in [
        ("hotels", "Hotel", "hotel"),
        ("airports", "Aeroporto", "airport"),
        ("networks", None, "network"),
    ]:
        for item in list(getattr(app, source_key, []) or []):
            legacy_id = f"{legacy_prefix}:{item.get('id', '')}"
            if legacy_id in existing_ids:
                continue
            mapped_type = tipo or LEGACY_TYPE_MAP.get(item.get("tipo"), "Parceiro corporativo")
            points.append(
                enrich_operational_point(
                    {
                        "nome": item.get("nome", ""),
                        "tipo": mapped_type,
                        "estado_uf": item.get("estado", ""),
                        "cidade_nome": item.get("cidade", ""),
                        "endereco": item.get("endereco", ""),
                        "observacoes": item.get("observacoes", ""),
                        "contato": item.get("contato", ""),
                        "status": "Operando" if item.get("status") == "Publicado" else "Pausado",
                        "portal_publicado": item.get("status") == "Publicado",
                        "legacy_source": source_key,
                        "legacy_source_id": legacy_id,
                    }
                )
            )
            existing_ids.add(legacy_id)
            changed = True

    if changed:
        app.operational_points = points
    return changed, changed


def driver_network_summary(driver):
    ids = list(driver.get("operational_point_ids") or [])
    if not ids:
        return []
    return ids
