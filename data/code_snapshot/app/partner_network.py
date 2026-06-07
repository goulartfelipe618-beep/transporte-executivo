"""Rede Comercial — modelo, slug/codigo, contribuidores, comissoes."""
from __future__ import annotations

import secrets
import string
import uuid
from datetime import datetime

from .company_model import slugify
from .partner_network_schema import (
    NETWORK_BRANDING_DEFAULTS,
    STATE_LEGACY_REDE,
    STATE_PARTNER_NETWORKS,
    TIPO_REDE_OPTIONS,
)

ENGINE_BASE = "https://engine.transporteexecutivo.com"
CODIGO_LEN = 6
HOTEL_TIPOS = {"HOTEL", "POUSADA", "HOSTEL", "RESORT"}


def _now():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _pct(raw, default=0.0):
    try:
        return min(max(round(float(str(raw or "").replace(",", ".")), 2), 0.0), 100.0)
    except ValueError:
        return default


def _ativo(record):
    if "ativo" in record:
        return bool(record.get("ativo"))
    return str(record.get("status", "Ativo")).lower() in {"ativo", "active", "true"}


def generate_codigo(records):
    alpha = string.ascii_uppercase + string.digits
    used = {str(r.get("codigo", r.get("codigo_acesso", ""))).upper() for r in records or []}
    for _ in range(500):
        code = "".join(secrets.choice(alpha) for _ in range(CODIGO_LEN))
        if code not in used:
            return code
    return secrets.token_hex(3).upper()[:CODIGO_LEN]


def _unique_slug(base, records, exclude=None):
    slug = slugify(base) or "rede"
    used = {str(r.get("slug", "")).lower() for r in records or [] if r.get("id") != exclude}
    if slug not in used:
        return slug
    n = 2
    while f"{slug}-{n}" in used:
        n += 1
    return f"{slug}-{n}"


def link_publico(partner):
    slug = str(partner.get("slug", "")).strip()
    code = str(partner.get("codigo", partner.get("codigo_acesso", ""))).strip()
    if slug and code:
        return f"{ENGINE_BASE}/{slug}/{code}"
    pid, token = str(partner.get("id", "")).strip(), str(partner.get("booking_token", "")).strip()
    if pid and token:
        return f"{ENGINE_BASE}/{pid}/{token}"
    return ""


booking_url = link_publico


def calc_commission(valor, rede_pct, contrib_pct_rede=0.0):
    valor = float(valor or 0)
    bruta = round(valor * float(rede_pct or 0) / 100, 2)
    contrib = round(bruta * float(contrib_pct_rede or 0) / 100, 2)
    return {
        "valor_total": valor,
        "comissao_rede_bruta": bruta,
        "comissao_contribuidor": contrib,
        "comissao_rede_liquida": round(bruta - contrib, 2),
    }


def is_hotel(partner):
    return str(partner.get("tipo_rede", "")).upper() in HOTEL_TIPOS


def normalize_contributor(record, partner_id, siblings=None):
    record = dict(record or {})
    siblings = list(siblings or [])
    nome = str(record.get("nome", "")).strip()
    ref = str(record.get("codigo_ref", "")).strip().lower() or slugify(nome)[:24] or "ref"
    return {
        "id": record.get("id") or f"nc-{len(siblings) + 1:06d}",
        "uuid": record.get("uuid") or str(uuid.uuid4()),
        "partner_id": partner_id,
        "nome": nome,
        "email": str(record.get("email", "")).strip().lower(),
        "codigo_ref": ref,
        "percentual_comissao": _pct(record.get("percentual_comissao", 0)),
        "ativo": record.get("ativo", True),
        "status": "Ativo" if record.get("ativo", True) else "Inativo",
        "created_at": record.get("created_at") or _iso(),
        "updated_at": _iso(),
    }


def normalize_partner_network(record, records=None):
    record = dict(record or {})
    records = list(records or [])
    rid = record.get("id") or f"red-{len(records) + 1:06d}"
    nome = str(record.get("nome_rede", record.get("nome", ""))).strip()
    slug = str(record.get("slug", "")).lower() or _unique_slug(nome, records, rid)
    codigo = str(record.get("codigo", record.get("codigo_acesso", ""))).upper() or generate_codigo(records)
    comissao = _pct(record.get("comissao_percentual", record.get("comissao_pct", record.get("comissao_rede"))))
    ativo = _ativo(record)
    tipo = str(record.get("tipo_rede", "AFILIADO")).upper().strip()
    if tipo not in TIPO_REDE_OPTIONS:
        tipo = "AFILIADO"
    saved = {
        **record,
        **{k: str(record.get(k, v) or v) for k, v in NETWORK_BRANDING_DEFAULTS.items()},
        "id": rid,
        "uuid": record.get("uuid") or str(uuid.uuid4()),
        "codigo": codigo,
        "codigo_acesso": codigo,
        "slug": slug,
        "portal_key": str(record.get("portal_key", slug)),
        "nome_rede": nome,
        "nome": nome,
        "tipo_rede": tipo,
        "telefone": str(record.get("telefone", "")).strip(),
        "whatsapp": str(record.get("whatsapp", record.get("telefone", ""))).strip(),
        "email": str(record.get("email", "")).strip().lower(),
        "cidade": str(record.get("cidade", "")).strip(),
        "estado": str(record.get("estado", "")).upper().strip(),
        "comissao_percentual": comissao,
        "comissao_pct": comissao,
        "comissao_rede": comissao,
        "ativo": ativo,
        "status": "Ativo" if ativo else "Inativo",
        "booking_token": record.get("booking_token") or secrets.token_urlsafe(48),
        "contribuidores": record.get("contribuidores") or [],
        "updated_at": _iso(),
        "atualizado_em": _now(),
    }
    if not saved.get("criado_em"):
        saved["criado_em"] = _now()
    if not saved.get("created_at"):
        saved["created_at"] = _iso()
    saved["link_publico"] = link_publico(saved)
    saved["booking_link"] = saved["link_publico"]
    return saved


def sync_partner_state(app):
    app.rede_empresas = list(getattr(app, STATE_PARTNER_NETWORKS, []) or [])
    flat = []
    for p in app.partner_networks:
        for c in p.get("contribuidores") or []:
            flat.append({**c, "partner_id": p.get("id")})
    app.network_contributors = flat


def _init_collections(app):
    for key in (
        STATE_PARTNER_NETWORKS,
        "network_contributors",
        "network_commissions",
        "contributor_commissions",
        "network_access_logs",
        "audit_log",
        STATE_LEGACY_REDE,
    ):
        if not hasattr(app, key):
            setattr(app, key, [])


def ensure_partner_networks(app):
    _init_collections(app)
    changed = False
    legacy = list(getattr(app, STATE_LEGACY_REDE, []) or [])
    if legacy and not app.partner_networks:
        app.partner_networks = [normalize_partner_network(x, []) for x in legacy]
        changed = True
    migrated = []
    for p in app.partner_networks:
        n = normalize_partner_network(p, migrated)
        if n != p:
            changed = True
        migrated.append(n)
    app.partner_networks = migrated
    sync_partner_state(app)
    return changed


def find_partner(app, slug=None, codigo=None, partner_id=None, token=None):
    ensure_partner_networks(app)
    slug, codigo = str(slug or "").lower(), str(codigo or "").upper()
    for p in app.partner_networks:
        ps, pc = str(p.get("slug", "")).lower(), str(p.get("codigo", p.get("codigo_acesso", ""))).upper()
        if slug and codigo and ps == slug and pc == codigo:
            return p
        if partner_id and token and str(p.get("id", "")) == str(partner_id) and str(p.get("booking_token", "")) == str(token):
            return p
        if partner_id and str(p.get("id", "")) == str(partner_id):
            return p
    return None


def find_contributor(partner, ref):
    ref = str(ref or "").strip().lower()
    if not ref:
        return None
    for c in partner.get("contribuidores") or []:
        if str(c.get("codigo_ref", "")).lower() == ref and c.get("ativo", True):
            return c
    return None


normalize_rede_empresa = normalize_partner_network
toggle_rede_status = lambda p: {**p, "status": "Inativo" if p.get("status") == "Ativo" else "Ativo", "ativo": p.get("status") == "Ativo"}
