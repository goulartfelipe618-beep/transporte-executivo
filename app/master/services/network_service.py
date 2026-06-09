"""Servico da Rede Comercial — espelha partner_network e UIs rede_*."""
from __future__ import annotations

from app.partner_network import (
    booking_url,
    ensure_partner_networks,
    normalize_contributor,
    normalize_partner_network,
    sync_partner_state,
    toggle_rede_status,
)
from app.partner_network_schema import NETWORK_BRANDING_DEFAULTS, TIPO_REDE_OPTIONS

REDE_STATUSES = ("Ativo", "Inativo")
COMMISSION_STATUS_OPTIONS = ("pendente", "pago", "cancelado")


def _persist(runtime):
    runtime.save_state()


def _partners(runtime):
    ensure_partner_networks(runtime)
    return list(getattr(runtime, "partner_networks", []) or [])


def _contributors_flat(runtime):
    ensure_partner_networks(runtime)
    rows = []
    for partner in _partners(runtime):
        for item in partner.get("contribuidores") or []:
            rows.append({**item, "partner_id": partner.get("id"), "partner_nome": partner.get("nome_rede") or partner.get("nome", "")})
    return rows


def _partner_map(runtime):
    return {str(p.get("id")): p for p in _partners(runtime)}


def partner_display(partner):
    comissao = partner.get("comissao_rede", partner.get("comissao_pct", 0))
    return {
        **partner,
        "comissao_display": f"{comissao:g}%",
        "link": booking_url(partner),
        "contribuidores_count": len(partner.get("contribuidores") or []),
    }


def contributor_display(contributor, partner=None):
    partner = partner or {}
    link = contributor_link(partner, contributor) if partner else ""
    return {
        **contributor,
        "status_label": "Ativo" if contributor.get("ativo", True) else "Inativo",
        "comissao_display": f'{contributor.get("percentual_comissao", 0):g}%',
        "partner_nome": contributor.get("partner_nome") or partner.get("nome_rede") or partner.get("nome", ""),
        "link": link,
    }


def contributor_link(partner, contributor):
    base = booking_url(partner)
    ref = str(contributor.get("codigo_ref", "")).strip()
    if not base or not ref:
        return ""
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}ref={ref}"


def money_display(value):
    amount = float(value or 0)
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def dashboard_context(runtime):
    ensure_partner_networks(runtime)
    partners = _partners(runtime)
    contributors = _contributors_flat(runtime)
    network_commissions = list(getattr(runtime, "network_commissions", []) or [])
    contributor_commissions = list(getattr(runtime, "contributor_commissions", []) or [])
    pending_net = sum(1 for row in network_commissions if str(row.get("status_pagamento", "")).lower() == "pendente")
    pending_contrib = sum(1 for row in contributor_commissions if str(row.get("status_pagamento", "")).lower() == "pendente")
    return {
        "partners_total": len(partners),
        "partners_active": sum(1 for p in partners if p.get("ativo", True)),
        "contributors_total": len(contributors),
        "commissions_total": len(network_commissions),
        "commissions_pending": pending_net,
        "contributor_commissions_total": len(contributor_commissions),
        "contributor_commissions_pending": pending_contrib,
    }


def list_partners(runtime):
    return [partner_display(p) for p in _partners(runtime)]


def find_partner(runtime, partner_id):
    partner_id = str(partner_id or "").strip()
    for partner in _partners(runtime):
        if str(partner.get("id")) == partner_id:
            return partner_display(partner)
    return None


def find_partner_raw(runtime, partner_id):
    partner_id = str(partner_id or "").strip()
    for partner in _partners(runtime):
        if str(partner.get("id")) == partner_id:
            return partner
    return None


def validate_partner_form(form_data, *, is_create=False):
    errors = []
    nome = str(form_data.get("nome_rede", "")).strip()
    comissao = str(form_data.get("comissao_rede", "")).strip()
    if not nome:
        errors.append("Informe o nome da rede.")
    if not comissao:
        errors.append("Informe a comissao da rede (%).")
    tipo = str(form_data.get("tipo_rede", "AFILIADO")).upper().strip()
    if tipo not in TIPO_REDE_OPTIONS:
        errors.append("Tipo de rede invalido.")
    status = str(form_data.get("status", "Ativo")).strip()
    if status not in REDE_STATUSES:
        errors.append("Status invalido.")
    return errors


def partner_form_fields():
    return {
        "identity": [
            ("nome_rede", "Nome da rede", "Ex.: Hotel Aurora", True),
            ("tipo_rede", "select", TIPO_REDE_OPTIONS),
            ("status", "select", REDE_STATUSES),
        ],
        "branding": [
            ("logo_url", "Logo (URL)", "https://.../logo.png", False),
            ("banner_url", "Banner (URL)", "https://.../banner.jpg", False),
            ("cor_primaria", "Cor primaria", "#0D1B2A", False),
            ("cor_secundaria", "Cor secundaria", "#D4AF37", False),
            ("texto_boas_vindas", "Texto de boas-vindas", "Mensagem no Motor", False),
        ],
        "contact": [
            ("telefone", "Telefone", "Telefone comercial", False),
            ("whatsapp", "WhatsApp", "WhatsApp comercial", False),
            ("email", "E-mail", "contato@empresa.com", False),
            ("cidade", "Cidade", "Cidade base", False),
            ("estado", "Estado (UF)", "UF", False),
            ("comissao_rede", "Comissao rede (%)", "Ex.: 10", True),
            ("observacoes", "Observacoes", "Informacoes internas", False),
        ],
        "branding_defaults": NETWORK_BRANDING_DEFAULTS,
        "tipo_options": TIPO_REDE_OPTIONS,
        "status_options": REDE_STATUSES,
    }


def create_partner(runtime, form_data):
    errors = validate_partner_form(form_data, is_create=True)
    if errors:
        return None, errors
    payload = normalize_partner_network(
        {**form_data, "nome": form_data.get("nome_rede")},
        _partners(runtime),
    )
    runtime.partner_networks.insert(0, payload)
    sync_partner_state(runtime)
    _persist(runtime)
    return partner_display(payload), []


def update_partner(runtime, partner_id, form_data):
    errors = validate_partner_form(form_data)
    if errors:
        return None, errors
    current = find_partner_raw(runtime, partner_id)
    if not current:
        return None, ["Parceiro nao encontrado."]
    payload = normalize_partner_network(
        {**current, **form_data, "nome": form_data.get("nome_rede"), "id": current.get("id")},
        [p for p in _partners(runtime) if str(p.get("id")) != str(partner_id)],
    )
    payload["contribuidores"] = current.get("contribuidores") or []
    for index, row in enumerate(runtime.partner_networks):
        if str(row.get("id")) == str(partner_id):
            runtime.partner_networks[index] = payload
            break
    sync_partner_state(runtime)
    _persist(runtime)
    return partner_display(payload), []


def toggle_partner(runtime, partner_id):
    current = find_partner_raw(runtime, partner_id)
    if not current:
        return None, ["Parceiro nao encontrado."]
    updated = toggle_rede_status(current)
    for index, row in enumerate(runtime.partner_networks):
        if str(row.get("id")) == str(partner_id):
            runtime.partner_networks[index] = {**row, **updated}
            break
    sync_partner_state(runtime)
    _persist(runtime)
    return partner_display(runtime.partner_networks[index]), []


def list_contributors(runtime, *, partner_id: str = ""):
    rows = _contributors_flat(runtime)
    if partner_id:
        rows = [row for row in rows if str(row.get("partner_id")) == str(partner_id)]
    partners = _partner_map(runtime)
    return [contributor_display(row, partners.get(str(row.get("partner_id")))) for row in rows]


def find_contributor(runtime, contributor_id):
    contributor_id = str(contributor_id or "").strip()
    for partner in _partners(runtime):
        for item in partner.get("contribuidores") or []:
            if str(item.get("id")) == contributor_id:
                row = {**item, "partner_id": partner.get("id"), "partner_nome": partner.get("nome_rede") or partner.get("nome", "")}
                return contributor_display(row, partner), partner
    return None, None


def validate_contributor_form(form_data):
    errors = []
    if not str(form_data.get("nome", "")).strip():
        errors.append("Informe o nome.")
    if not str(form_data.get("codigo_ref", "")).strip():
        errors.append("Informe o codigo ref.")
    if not str(form_data.get("partner_id", "")).strip():
        errors.append("Selecione o parceiro.")
    return errors


def _set_partner_contributors(runtime, partner_id, siblings):
    for index, row in enumerate(runtime.partner_networks):
        if str(row.get("id")) == str(partner_id):
            runtime.partner_networks[index] = {**row, "contribuidores": siblings}
            break
    sync_partner_state(runtime)
    _persist(runtime)


def create_contributor(runtime, form_data):
    errors = validate_contributor_form(form_data)
    if errors:
        return None, errors
    partner = find_partner_raw(runtime, form_data.get("partner_id"))
    if not partner:
        return None, ["Parceiro nao encontrado."]
    siblings = list(partner.get("contribuidores") or [])
    saved = normalize_contributor(form_data, partner.get("id"), siblings)
    siblings.append(saved)
    _set_partner_contributors(runtime, partner.get("id"), siblings)
    return contributor_display(saved, partner), []


def update_contributor(runtime, contributor_id, form_data):
    current, partner = find_contributor(runtime, contributor_id)
    if not current or not partner:
        return None, ["Contribuidor nao encontrado."]
    partner_id = str(form_data.get("partner_id") or current.get("partner_id") or partner.get("id"))
    errors = validate_contributor_form({**form_data, "partner_id": partner_id})
    if errors:
        return None, errors
    target_partner = find_partner_raw(runtime, partner_id)
    if not target_partner:
        return None, ["Parceiro nao encontrado."]

    old_partner_id = str(partner.get("id"))
    if old_partner_id != str(partner_id):
        old_siblings = [c for c in partner.get("contribuidores") or [] if str(c.get("id")) != str(contributor_id)]
        _set_partner_contributors(runtime, old_partner_id, old_siblings)
        target_partner = find_partner_raw(runtime, partner_id)
        siblings = list(target_partner.get("contribuidores") or [])
    else:
        siblings = list(partner.get("contribuidores") or [])

    saved = normalize_contributor({**current, **form_data, "id": contributor_id}, partner_id, siblings)
    updated = False
    for index, row in enumerate(siblings):
        if str(row.get("id")) == str(contributor_id):
            siblings[index] = saved
            updated = True
            break
    if not updated:
        siblings.append(saved)
    _set_partner_contributors(runtime, partner_id, siblings)
    target_partner = find_partner_raw(runtime, partner_id)
    return contributor_display(saved, target_partner), []


def delete_contributor(runtime, contributor_id):
    _contrib, partner = find_contributor(runtime, contributor_id)
    if not partner:
        return False, ["Contribuidor nao encontrado."]
    siblings = [c for c in partner.get("contribuidores") or [] if str(c.get("id")) != str(contributor_id)]
    _set_partner_contributors(runtime, partner.get("id"), siblings)
    return True, []


def _reservation_href(commission, reservations_index):
    numero = str(commission.get("reservation_numero") or "").strip()
    if numero:
        return f"/reservas/{numero}"
    res_id = str(commission.get("reservation_id") or "").strip()
    reservation = reservations_index.get(res_id)
    if reservation and reservation.get("numero"):
        return f"/reservas/{reservation['numero']}"
    if res_id:
        return f"/reservas/{res_id}"
    return ""


def list_commissions(runtime, *, status: str = "", partner_id: str = ""):
    ensure_partner_networks(runtime)
    partners = _partner_map(runtime)
    reservations = getattr(runtime, "reservations", []) or []
    reservations_index = {}
    for item in reservations:
        reservations_index[str(item.get("id"))] = item
        if item.get("numero"):
            reservations_index[str(item.get("numero"))] = item

    rows = []
    for item in getattr(runtime, "network_commissions", []) or []:
        status_value = str(item.get("status_pagamento", "pendente")).lower()
        if status and status_value != status.lower():
            continue
        pid = str(item.get("partner_id") or "")
        if partner_id and pid != str(partner_id):
            continue
        partner = partners.get(pid, {})
        rows.append(
            {
                **item,
                "kind": "rede",
                "partner_nome": partner.get("nome_rede") or partner.get("nome", pid or "—"),
                "valor_display": money_display(item.get("valor_comissao", 0)),
                "valor_base_display": money_display(item.get("valor_base", 0)),
                "status_label": status_value.capitalize(),
                "reservation_href": _reservation_href(item, reservations_index),
            }
        )

    for item in getattr(runtime, "contributor_commissions", []) or []:
        status_value = str(item.get("status_pagamento", "pendente")).lower()
        if status and status_value != status.lower():
            continue
        pid = str(item.get("partner_id") or "")
        if partner_id and pid != str(partner_id):
            continue
        partner = partners.get(pid, {})
        contrib = None
        for c in partner.get("contribuidores") or []:
            if str(c.get("id")) == str(item.get("contributor_id")):
                contrib = c
                break
        rows.append(
            {
                **item,
                "kind": "contribuidor",
                "partner_nome": partner.get("nome_rede") or partner.get("nome", pid or "—"),
                "contributor_nome": (contrib or {}).get("nome", item.get("contributor_id", "—")),
                "valor_display": money_display(item.get("valor_comissao", 0)),
                "valor_base_display": "—",
                "status_label": status_value.capitalize(),
                "reservation_href": _reservation_href(item, reservations_index),
            }
        )

    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows


def commissions_summary(runtime):
    rows = list_commissions(runtime)
    return {
        "total": len(rows),
        "pendente": sum(1 for row in rows if str(row.get("status_pagamento", "")).lower() == "pendente"),
        "pago": sum(1 for row in rows if str(row.get("status_pagamento", "")).lower() == "pago"),
        "rede": sum(1 for row in rows if row.get("kind") == "rede"),
        "contribuidor": sum(1 for row in rows if row.get("kind") == "contribuidor"),
    }


def partner_choices(runtime):
    return [{"id": p.get("id"), "nome": p.get("nome_rede") or p.get("nome", "")} for p in _partners(runtime)]
