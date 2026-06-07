"""Rede e branding via Gateway Master."""

from typing import Any, Optional

from app.clients.gateway_api import GatewayAPIClient, GatewayAPIError


HOTEL_TYPES = frozenset({"hotel", "pousada", "resort", "hospedagem"})


def is_hotel_like(network_type: Optional[str]) -> bool:
    return bool(network_type and network_type.lower() in HOTEL_TYPES)


def normalize_network(raw: dict[str, Any]) -> dict[str, Any]:
    if "data" in raw and isinstance(raw["data"], dict):
        raw = raw["data"]
    colors = raw.get("colors") or {}
    if not isinstance(colors, dict):
        colors = {}
    return {
        "name": raw.get("name") or raw.get("network_name") or raw.get("nome_rede") or "Rede",
        "slug": raw.get("slug", ""),
        "code": raw.get("code") or raw.get("codigo", ""),
        "cidade": raw.get("cidade") or raw.get("city", ""),
        "estado": raw.get("estado") or raw.get("state", ""),
        "logo_url": raw.get("logo_url") or raw.get("logo", ""),
        "banner_url": raw.get("banner_url") or raw.get("banner", ""),
        "colors": {
            "primary": colors.get("primary", "#0D1B2A"),
            "accent": colors.get("accent", "#D4AF37"),
            "background": colors.get("background", "#F8F9FA"),
        },
        "type": (raw.get("type") or raw.get("network_type") or "network").lower(),
        "welcome_text": raw.get("welcome_text") or raw.get("welcome", ""),
        "default_origin": raw.get("default_origin") or raw.get("origin_default", ""),
        "contributors": raw.get("contributors") or [],
        "commission_rules": raw.get("commission_rules") or {},
        "whatsapp_support": raw.get("whatsapp_support") or raw.get("whatsapp", ""),
    }


def resolve_contributor_ref(network: dict[str, Any], ref_query: Optional[str]) -> Optional[str]:
    if not ref_query:
        return None
    return ref_query.strip().upper()


async def fetch_network(slug: str, codigo: str) -> dict[str, Any]:
    client = GatewayAPIClient()
    raw = await client.get_network(slug, codigo)
    return normalize_network(raw)


def network_city(network: dict[str, Any]) -> str:
    return str(network.get("cidade") or network.get("city") or "").strip()
