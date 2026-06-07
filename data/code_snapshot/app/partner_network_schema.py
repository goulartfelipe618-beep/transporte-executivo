"""Constantes de estado local e tabelas Supabase da Rede Comercial."""
STATE_PARTNER_NETWORKS = "partner_networks"
STATE_LEGACY_REDE = "rede_empresas"

TABLE_PARTNER_NETWORKS = "partner_networks"
TABLE_NETWORK_COMMISSIONS = "network_commissions"
TABLE_CONTRIBUTOR_COMMISSIONS = "contributor_commissions"
TABLE_TRANSPORT_REQUESTS = "transport_requests"
TABLE_RESERVATIONS = "reservations"
TABLE_AUDIT_LOG = "audit_log"

TIPO_REDE_OPTIONS = (
    "HOTEL",
    "POUSADA",
    "HOSTEL",
    "RESORT",
    "AFILIADO",
    "EMPRESA",
    "AGENCIA",
    "EVENTO",
)

NETWORK_BRANDING_DEFAULTS = {
    "logo_url": "",
    "banner_url": "",
    "cor_primaria": "#0D1B2A",
    "cor_secundaria": "#D4AF37",
    "texto_boas_vindas": "Reserve seu transporte executivo com seguranca e praticidade.",
}
