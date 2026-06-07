"""Persistencia Rede/Motor -> Supabase (paralelo ao JSON local)."""
from __future__ import annotations

from datetime import datetime, timezone

from ..partner_network_schema import (
    TABLE_AUDIT_LOG,
    TABLE_CONTRIBUTOR_COMMISSIONS,
    TABLE_NETWORK_COMMISSIONS,
    TABLE_PARTNER_NETWORKS,
    TABLE_RESERVATIONS,
    TABLE_TRANSPORT_REQUESTS,
)
from .supabase_client import insert_row, is_configured, select_one


def _parse_valor(raw):
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw or "").replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return 0.0


def _partner_uuid(partner):
    row = select_one(TABLE_PARTNER_NETWORKS, filters={"legacy_admin_id": partner.get("id")})
    return row.get("id") if row else None


def _contributor_uuid(contributor):
    if not contributor:
        return None
    row = select_one("network_contributors", filters={"legacy_admin_id": contributor.get("id")})
    return row.get("id") if row else None


def sync_network_reservation(app, *, partner, contributor, treq, reservation, net_com, ccom, audit):
    if not is_configured():
        return {"ok": False, "skipped": True, "reason": "supabase_not_configured"}

    partner_uuid = _partner_uuid(partner)
    if not partner_uuid:
        return {"ok": False, "skipped": True, "reason": "partner_not_in_supabase"}

    contrib_uuid = _contributor_uuid(contributor)
    valor = _parse_valor(reservation.get("valor"))

    treq_row = insert_row(
        TABLE_TRANSPORT_REQUESTS,
        {
            "legacy_admin_id": treq.get("id"),
            "partner_id": partner_uuid,
            "partner_slug": partner.get("slug"),
            "partner_code": partner.get("codigo"),
            "contributor_id": contrib_uuid,
            "contributor_code": (contributor or {}).get("codigo_ref", ""),
            "origem": treq.get("origem"),
            "destino": treq.get("destino"),
            "data": treq.get("data"),
            "hora": treq.get("hora"),
            "nome": treq.get("nome"),
            "telefone": treq.get("telefone"),
            "email": treq.get("email"),
            "passageiros": treq.get("passageiros"),
            "status": treq.get("status"),
            "source": treq.get("source"),
            "flow": treq.get("flow"),
            "canal_origem": treq.get("canal_origem"),
            "via_qr": treq.get("via_qr", False),
            "valor_estimado": treq.get("valor_estimado"),
            "origem_fonte": "Motor de Reservas",
        },
    )

    res_row = insert_row(
        TABLE_RESERVATIONS,
        {
            "legacy_admin_id": reservation.get("id"),
            "numero": reservation.get("numero"),
            "partner_id": partner_uuid,
            "partner_slug": partner.get("slug"),
            "partner_code": partner.get("codigo"),
            "contributor_id": contrib_uuid,
            "contributor_code": (contributor or {}).get("codigo_ref", ""),
            "cliente": reservation.get("cliente"),
            "trajeto": reservation.get("trajeto"),
            "origem": treq.get("origem"),
            "destino": treq.get("destino"),
            "data": reservation.get("data"),
            "status": reservation.get("status"),
            "valor": valor,
            "tipo": reservation.get("tipo"),
            "source": reservation.get("source"),
            "flow": reservation.get("flow"),
            "canal_origem": reservation.get("canal_origem"),
            "via_qr": reservation.get("via_qr", False),
            "transport_request_legacy_id": treq.get("id"),
            "dados_extra": {
                "partner_nome": partner.get("nome_rede"),
                "contributor_nome": (contributor or {}).get("nome", ""),
            },
        },
    )

    res_uuid = res_row.get("id") if res_row else None
    treq_uuid = treq_row.get("id") if treq_row else None

    insert_row(
        TABLE_NETWORK_COMMISSIONS,
        {
            "legacy_admin_id": net_com.get("id"),
            "partner_id": partner_uuid,
            "reservation_id": res_uuid,
            "reservation_numero": reservation.get("numero"),
            "transport_request_id": treq_uuid,
            "valor_base": net_com.get("valor_base"),
            "percentual": net_com.get("percentual"),
            "valor_bruto": net_com.get("valor_bruto"),
            "valor_comissao": net_com.get("valor_comissao"),
            "status_pagamento": net_com.get("status_pagamento"),
        },
    )

    if ccom and contributor:
        insert_row(
            TABLE_CONTRIBUTOR_COMMISSIONS,
            {
                "legacy_admin_id": ccom.get("id"),
                "partner_id": partner_uuid,
                "contributor_id": contrib_uuid,
                "reservation_id": res_uuid,
                "reservation_numero": reservation.get("numero"),
                "percentual": ccom.get("percentual"),
                "valor_comissao": ccom.get("valor_comissao"),
                "status_pagamento": ccom.get("status_pagamento"),
            },
        )

    insert_row(
        TABLE_AUDIT_LOG,
        {
            "legacy_admin_id": audit.get("id"),
            "action": audit.get("action"),
            "partner_id": partner_uuid,
            "reservation_id": res_uuid,
            "record_table": "reservations",
            "record_id": reservation.get("id"),
            "payload": audit.get("payload", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {"ok": True, "supabase_reservation_id": res_uuid, "supabase_transport_request_id": treq_uuid}
