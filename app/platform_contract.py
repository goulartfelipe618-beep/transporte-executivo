"""
Espelho executavel do PLATFORM_CONTRACT v1.0.0 (Sistema Master).

Website espelho: core/integrations/platform_contract.py
DTOs Website: core/public_dtos.py, core/integrations/mappers.py, core/integrations/api_gateway.py
"""
from __future__ import annotations

CONTRACT_VERSION = "1.0.0"
CONTRACT_TARGET_SYSTEM = "system"
CONTRACT_TARGET_WEBSITE = "website"

# --- DTOs (Website) ↔ API paths ---

DTO_COVERAGE_SUMMARY = "CoverageSummary"
DTO_PUBLIC_LOCATION = "PublicLocation"
DTO_PUBLIC_VEHICLE = "PublicVehicle"

DTO_API_MAP = {
    DTO_COVERAGE_SUMMARY: "/api/v1/public/statistics",
    DTO_PUBLIC_LOCATION: "/api/v1/public/locations",
    DTO_PUBLIC_VEHICLE: "/api/v1/public/vehicles",
}

WEBSITE_SYNC_FIELDS = ("id_admin", "website_slug", "website_path")

# --- API v1 ---

API_V1_PREFIX = "/api/v1"

API_PUBLIC_STATISTICS = f"{API_V1_PREFIX}/public/statistics"
API_PUBLIC_STATS = f"{API_V1_PREFIX}/public/stats"
API_PUBLIC_COVERAGE = f"{API_V1_PREFIX}/public/coverage"
API_PUBLIC_VEHICLES = f"{API_V1_PREFIX}/public/vehicles"
API_PUBLIC_AIRPORTS = f"{API_V1_PREFIX}/public/airports"
API_PUBLIC_HOTELS = f"{API_V1_PREFIX}/public/hotels"
API_PUBLIC_EVENTS = f"{API_V1_PREFIX}/public/events"
API_PUBLIC_LOCATIONS_AGGREGATE = f"{API_V1_PREFIX}/public/locations"
API_PUBLIC_SYNC_LOCATIONS = f"{API_V1_PREFIX}/public/sync/locations"
API_PUBLIC_SYNC_STATISTICS = f"{API_V1_PREFIX}/public/sync/statistics"

API_PUBLIC_LOCATIONS_BASE = f"{API_V1_PREFIX}/public/locations"
API_PUBLIC_LOCATION_DETAIL_BASE = API_PUBLIC_LOCATIONS_BASE
LOCATION_LEVELS = (
    "states",
    "cities",
    "airports",
    "hotels",
    "events",
    "partners",
    "hubs",
    "support-points",
)

API_PUBLIC_LOCATIONS_STATES = f"{API_PUBLIC_LOCATIONS_BASE}/states"
API_PUBLIC_LOCATIONS_CITIES = f"{API_PUBLIC_LOCATIONS_BASE}/cities"
API_PUBLIC_LOCATIONS_AIRPORTS = f"{API_PUBLIC_LOCATIONS_BASE}/airports"
API_PUBLIC_LOCATIONS_HOTELS = f"{API_PUBLIC_LOCATIONS_BASE}/hotels"
API_PUBLIC_LOCATIONS_EVENTS = f"{API_PUBLIC_LOCATIONS_BASE}/events"
API_PUBLIC_LOCATIONS_PARTNERS = f"{API_PUBLIC_LOCATIONS_BASE}/partners"
API_PUBLIC_LOCATIONS_HUBS = f"{API_PUBLIC_LOCATIONS_BASE}/hubs"
API_PUBLIC_LOCATIONS_SUPPORT_POINTS = f"{API_PUBLIC_LOCATIONS_BASE}/support-points"

LEVEL_TO_PATH = {level: f"{API_PUBLIC_LOCATIONS_BASE}/{level}" for level in LOCATION_LEVELS}


def api_public_location_detail(website_slug: str) -> str:
    return f"{API_PUBLIC_LOCATIONS_BASE}/{website_slug}"


# Inbound (Website → Sistema)
API_INBOUND_COMPANY_LEAD = f"{API_V1_PREFIX}/webhooks/inbound/company.lead"
API_INBOUND_DRIVER_APPLICATION = f"{API_V1_PREFIX}/webhooks/inbound/driver.application"
API_INBOUND_RESERVATION_REQUEST = f"{API_V1_PREFIX}/webhooks/inbound/reservation.request"

# Rede Comercial / Motor de Reservas (publico, sem segredo webhook)
API_NETWORK_BASE = f"{API_V1_PREFIX}/network"
API_INBOUND_NETWORK_RESERVATION = f"{API_V1_PREFIX}/webhooks/inbound/network.reservation"
INBOUND_EVENT_NETWORK_RESERVATION = "network.reservation"

# Outbound (Sistema → Website receiver)
API_WEBHOOK_OUTBOUND_WEBSITE = f"{API_V1_PREFIX}/webhooks/outbound/"

# Private / legado
API_PRIVATE_DRIVER_PREFIX = f"{API_V1_PREFIX}/private/driver"
API_PRIVATE_COMPANY_PREFIX = f"{API_V1_PREFIX}/private/company"
LEGACY_DRIVER_PORT = 8765
LEGACY_COMPANY_PORT = 8766
LEGACY_DRIVER_API_PREFIX = "/api/driver"
LEGACY_COMPANY_API_PREFIX = "/api/company"

DEPRECATED_API_PATHS = (
    "/estatisticas",
    "/inbound/motoristas/cadastro",
    "/api/inbound/company-leads",
    "/api/inbound/driver-leads",
    "/api/inbound/transport-requests",
    "/api/outbound/coverage",
    "/api/v1/public/coverage/summary",
)

# --- Events ---

EVENT_DRIVER_CREATED = "driver.created"
EVENT_DRIVER_UPDATED = "driver.updated"
EVENT_COMPANY_CREATED = "company.created"
EVENT_COMPANY_UPDATED = "company.updated"
EVENT_LOCATION_CREATED = "location.created"
EVENT_LOCATION_UPDATED = "location.updated"
EVENT_LOCATION_DELETED = "location.deleted"
EVENT_VEHICLE_CREATED = "vehicle.created"
EVENT_VEHICLE_UPDATED = "vehicle.updated"
EVENT_LEAD_CREATED = "lead.created"
EVENT_RESERVATION_CREATED = "reservation.created"
EVENT_RESERVATION_UPDATED = "reservation.updated"

OUTBOUND_WEBHOOK_EVENTS = (
    EVENT_DRIVER_CREATED,
    EVENT_DRIVER_UPDATED,
    EVENT_COMPANY_CREATED,
    EVENT_COMPANY_UPDATED,
    EVENT_LOCATION_CREATED,
    EVENT_LOCATION_UPDATED,
    EVENT_LOCATION_DELETED,
    EVENT_VEHICLE_CREATED,
    EVENT_VEHICLE_UPDATED,
    EVENT_LEAD_CREATED,
    EVENT_RESERVATION_CREATED,
    EVENT_RESERVATION_UPDATED,
)

OUTBOUND_WEBSITE_EVENTS = (
    EVENT_LOCATION_CREATED,
    EVENT_LOCATION_UPDATED,
    EVENT_LOCATION_DELETED,
    EVENT_VEHICLE_CREATED,
    EVENT_VEHICLE_UPDATED,
    EVENT_DRIVER_CREATED,
    EVENT_DRIVER_UPDATED,
    EVENT_COMPANY_CREATED,
    EVENT_COMPANY_UPDATED,
)

INTERNAL_EVENTS = (
    "site.company_lead.received",
    "site.driver_lead.received",
    "site.transport_request.received",
    "inbound.manual.created",
    "inbound.status.changed",
)

INBOUND_EVENT_COMPANY_LEAD = "company.lead"
INBOUND_EVENT_DRIVER_APPLICATION = "driver.application"
INBOUND_EVENT_RESERVATION_REQUEST = "reservation.request"

INBOUND_WEBHOOK_EVENTS = (
    INBOUND_EVENT_COMPANY_LEAD,
    INBOUND_EVENT_DRIVER_APPLICATION,
    INBOUND_EVENT_RESERVATION_REQUEST,
)

INBOUND_ALIASES = {
    "company-leads": INBOUND_EVENT_COMPANY_LEAD,
    "driver-leads": INBOUND_EVENT_DRIVER_APPLICATION,
}

INBOUND_EVENT_TO_PATH = {
    INBOUND_EVENT_COMPANY_LEAD: API_INBOUND_COMPANY_LEAD,
    INBOUND_EVENT_DRIVER_APPLICATION: API_INBOUND_DRIVER_APPLICATION,
    INBOUND_EVENT_RESERVATION_REQUEST: API_INBOUND_RESERVATION_REQUEST,
}

INBOUND_API_PATHS = INBOUND_EVENT_TO_PATH

GATEWAY_PORT = 8770
AUTOMATION_WEBHOOK_PORT = 8771
ENV_GATEWAY_HOST = "INTEGRACAO_GATEWAY_HOST"
ENV_GATEWAY_WEBHOOK_SECRET = "GATEWAY_WEBHOOK_SECRET"
ENV_WEBHOOK_OUTBOUND_URL = "WEBHOOK_OUTBOUND_URL"


def inbound_api_path(event: str) -> str:
    return INBOUND_API_PATHS[event]

ENTITY_COMPANY = "company"
ENTITY_COMPANY_USER = "company.user"
ENTITY_COST_CENTER = "cost_center"
ENTITY_DRIVER = "driver"
ENTITY_VEHICLE = "vehicle"
ENTITY_RESERVATION = "reservation"
ENTITY_RESERVATION_REQUEST = "reservation.request"
ENTITY_COMPANY_LEAD = "company.lead"
ENTITY_DRIVER_APPLICATION = "driver.application"
ENTITY_STATE = "state"
ENTITY_CITY = "city"
ENTITY_OPERATIONAL_POINT = "operational_point"

ENTITY_ID_PREFIXES = {
    ENTITY_COMPANY: "emp-",
    ENTITY_COMPANY_USER: "usr-",
    ENTITY_COST_CENTER: "cc-",
    ENTITY_COMPANY_LEAD: "clead-",
    ENTITY_DRIVER_APPLICATION: "dlead-",
    ENTITY_RESERVATION_REQUEST: "treq-",
    ENTITY_OPERATIONAL_POINT: "op-",
    "hotel_legacy": "htl-",
    "airport_legacy": "apt-",
    "network_legacy": "net-",
}

LOCATION_MODE_MANUAL = "manual"
LOCATION_MODE_NETWORK = "network"
LOCATION_MODE_NETWORK_LEGACY = "rede"

WEBSITE_TYPE_PREFIX = {
    "Aeroporto": "aeroporto",
    "Hotel": "hotel",
    "Centro de eventos": "centro-de-eventos",
    "Centro de convencoes": "centro-de-convencoes",
    "Hub operacional": "hub",
    "Parceiro corporativo": "parceiro",
    "Ponto de apoio": "ponto-de-apoio",
}

LOCATION_SEGMENT_BY_TYPE = {
    "Aeroporto": "airports",
    "Hotel": "hotels",
    "Centro de eventos": "events",
    "Centro de convencoes": "events",
    "Hub operacional": "hubs",
    "Parceiro corporativo": "partners",
    "Ponto de apoio": "support-points",
}

WEBSITE_ROUTES = {
    "cobertura_nacional": "/cobertura-nacional/",
    "cobertura_index": "/cobertura/",
    "aeroportos_index": "/aeroportos/",
    "hoteis_index": "/hoteis/",
    "frota_index": "/frota/",
    "veiculos_index": "/veiculos/",
    "public_location_slug": "/<website_slug>/",
}

WEBSITE_SEO_PATHS = (
    "/cobertura-nacional",
    "/aeroportos",
    "/hoteis",
    "/centros-de-eventos",
    "/parceiros",
    "/frota",
)

SCHEMA_BY_TIPO = {
    "Aeroporto": "Airport",
    "Hotel": "Hotel",
    "Centro de eventos": "EventVenue",
    "Centro de convencoes": "EventVenue",
    "Hub operacional": "LocalBusiness",
    "Parceiro corporativo": "LocalBusiness",
    "Ponto de apoio": "LocalBusiness",
}

# Env vars (Website)
ENV_API_ENABLED = "INTEGRACAO_API_ENABLED"
ENV_API_BASE_URL = "INTEGRACAO_API_BASE_URL"
ENV_WEBHOOK_ENABLED = "INTEGRACAO_WEBHOOK_ENABLED"
ENV_WEBHOOK_URL = "INTEGRACAO_WEBHOOK_URL"
ENV_WEBHOOK_SECRET = "INTEGRACAO_WEBHOOK_SECRET"

DATA_CLASS_PUBLIC = "publico"
DATA_CLASS_RESTRICTED = "restrito"
DATA_CLASS_INTERNAL = "interno"
DATA_CLASS_SECRET = "sigiloso"

NEVER_EXPOSE_TO_WEBSITE = frozenset(
    {
        "app_state.json",
        "reservations_full",
        "financial",
        "driver_documents",
        "company_contracts",
        "passwords",
        "cpf",
        "cnh",
        "cnh_photos",
    }
)

RESERVATION_WEBHOOK_EVENTS = {EVENT_RESERVATION_CREATED, EVENT_RESERVATION_UPDATED}


def build_webhook_envelope(event: str, entity_type: str, entity_id: str, payload: dict | None = None, *, target: str = CONTRACT_TARGET_WEBSITE) -> dict:
    from datetime import datetime, timezone

    return {
        "event": event,
        "contract_version": CONTRACT_VERSION,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "target": target,
        "occurred_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload": dict(payload or {}),
    }


def build_inbound_envelope(event: str, entity_type: str, payload: dict | None = None) -> dict:
    return build_webhook_envelope(event, entity_type, "", payload, target=CONTRACT_TARGET_SYSTEM)


def normalize_location_mode(mode: str) -> str:
    mode = str(mode or "").lower().strip()
    if mode in {LOCATION_MODE_NETWORK, LOCATION_MODE_NETWORK_LEGACY}:
        return LOCATION_MODE_NETWORK
    return LOCATION_MODE_MANUAL


def location_api_path_for_type(tipo: str) -> str:
    segment = LOCATION_SEGMENT_BY_TYPE.get(tipo, "support-points")
    return f"{API_PUBLIC_LOCATIONS_BASE}/{segment}"


def map_operational_point_to_public_location(point: dict) -> dict:
    """Mapeia ponto do Sistema → DTO PublicLocation (contrato API)."""
    point = dict(point or {})
    return {
        "id": point.get("id", ""),
        "entity_type": ENTITY_OPERATIONAL_POINT,
        "nome": point.get("nome", ""),
        "tipo": point.get("tipo", ""),
        "estado_uf": point.get("estado_uf", ""),
        "cidade_nome": point.get("cidade_nome", ""),
        "endereco": point.get("endereco", ""),
        "website_slug": point.get("website_slug", ""),
        "website_path": point.get("website_path", ""),
        "portal_publicado": bool(point.get("portal_publicado", True)),
        "id_admin": point.get("id", ""),
    }


def map_vehicle_to_public_vehicle(vehicle: dict) -> dict:
    vehicle = dict(vehicle or {})
    return {
        "id": vehicle.get("id") or vehicle.get("placa", ""),
        "entity_type": ENTITY_VEHICLE,
        "categoria": vehicle.get("tipo_veiculo") or vehicle.get("categoria", ""),
        "capacidade": vehicle.get("capacidade", vehicle.get("passageiros", "")),
        "bagagens": vehicle.get("bagagens", ""),
        "aplicacao": vehicle.get("aplicacao", vehicle.get("tipo_veiculo", "")),
        "marca": vehicle.get("marca", ""),
        "modelo": vehicle.get("modelo", ""),
        "foto": vehicle.get("capa", ""),
        "id_admin": vehicle.get("id") or vehicle.get("placa", ""),
    }


def build_coverage_summary(app) -> dict:
    """Monta DTO CoverageSummary a partir do estado do Sistema."""
    clients = list(getattr(app, "clients", []))
    drivers = list(getattr(app, "drivers", []))
    vehicles = list(getattr(app, "vehicles", []))
    points = list(getattr(app, "operational_points", []))

    corporate = [c for c in clients if c.get("tipo_pessoa") == "juridica" or c.get("cnpj")]
    active_corporate = [
        c for c in corporate if str(c.get("status_empresa", c.get("status", "Ativa"))).lower() not in {"inativa", "bloqueada"}
    ]
    homologated = [
        d
        for d in drivers
        if str(d.get("status_operacional", d.get("frota", ""))).lower() in {"ativo", "homologado", "operando"}
    ]
    published_vehicles = [
        v
        for v in vehicles
        if str(v.get("status", "Ativo")).lower() in {"ativo", "operando"}
        and str(v.get("portal_publicado", True)).lower() not in {"nao", "false", "0"}
    ]
    active_points = [p for p in points if p.get("status") == "Operando" and p.get("portal_publicado", True)]
    states = {p.get("estado_uf") for p in active_points if p.get("estado_uf")}
    cities = {(p.get("estado_uf"), p.get("cidade_nome")) for p in active_points if p.get("cidade_nome")}
    by_type: dict[str, int] = {}
    for point in active_points:
        tipo = point.get("tipo", "Hub operacional")
        by_type[tipo] = by_type.get(tipo, 0) + 1

    return {
        "contract_version": CONTRACT_VERSION,
        "companies_active": len(active_corporate) or len(corporate),
        "companies_total": len(corporate),
        "drivers_homologated": len(homologated) or len(drivers),
        "states_covered": len(states),
        "cities_covered": len(cities),
        "operational_points_total": len(active_points),
        "operational_points_by_type": by_type,
        "vehicles_published": len(published_vehicles),
    }
