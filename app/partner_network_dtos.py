"""DTO publico do Motor — GET /api/v1/network/{slug}/{codigo}."""
from __future__ import annotations

from .platform_contract import CONTRACT_VERSION

NETWORK_CONFIG_FIELDS = (
    "nome_rede",
    "tipo_rede",
    "logo_url",
    "banner_url",
    "cor_primaria",
    "cor_secundaria",
    "texto_boas_vindas",
    "telefone",
    "whatsapp",
    "email",
    "cidade",
    "estado",
    "comissao_rede",
    "status",
)


def _comissao_rede(partner):
    return float(
        partner.get("comissao_rede")
        or partner.get("comissao_percentual")
        or partner.get("comissao_pct")
        or 0
    )


def build_network_config(partner, contributor=None):
    dto = {
        "nome_rede": partner.get("nome_rede") or partner.get("nome", ""),
        "tipo_rede": partner.get("tipo_rede", "AFILIADO"),
        "logo_url": partner.get("logo_url", ""),
        "banner_url": partner.get("banner_url", ""),
        "cor_primaria": partner.get("cor_primaria", "#0D1B2A"),
        "cor_secundaria": partner.get("cor_secundaria", "#D4AF37"),
        "texto_boas_vindas": partner.get("texto_boas_vindas", ""),
        "telefone": partner.get("telefone", ""),
        "whatsapp": partner.get("whatsapp", partner.get("telefone", "")),
        "email": partner.get("email", ""),
        "cidade": partner.get("cidade", ""),
        "estado": partner.get("estado", ""),
        "comissao_rede": _comissao_rede(partner),
        "status": partner.get("status", "Ativo" if partner.get("ativo", True) else "Inativo"),
    }
    if contributor:
        dto["contributor"] = {
            "id": contributor.get("id", ""),
            "nome": contributor.get("nome", ""),
            "codigo_ref": contributor.get("codigo_ref", ""),
            "percentual_comissao": contributor.get("percentual_comissao", 0),
        }
    return dto


def build_network_api_response(partner, contributor=None):
    return {
        "contract_version": CONTRACT_VERSION,
        "partner_id": partner.get("id", ""),
        "slug": partner.get("slug", ""),
        "codigo": partner.get("codigo", partner.get("codigo_acesso", "")),
        "link_publico": partner.get("link_publico") or partner.get("booking_link", ""),
        **build_network_config(partner, contributor),
    }
