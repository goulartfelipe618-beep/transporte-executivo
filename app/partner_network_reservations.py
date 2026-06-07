"""Registro de reservas originadas pelo Motor de Reservas / Rede Comercial."""
from __future__ import annotations

import uuid
from datetime import datetime

from .partner_network import calc_commission, find_contributor, find_partner, sync_partner_state
from .platform import log_event, next_record_id
from .reservation_numbers import next_reservation_number

SOURCE, FLOW = "network", "express"


def _now():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _valor(payload):
    raw = payload.get("valor_total") or payload.get("valor") or payload.get("valor_estimado") or 0
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return 0.0


def write_audit(app, action, partner_id, payload=None):
    if not hasattr(app, "audit_log"):
        app.audit_log = []
    entry = {
        "id": next_record_id("aud", app.audit_log),
        "action": action,
        "partner_id": partner_id,
        "payload": dict(payload or {}),
        "created_at": _iso(),
    }
    app.audit_log.insert(0, entry)
    app.audit_log = app.audit_log[:5000]
    return entry


def register_network_reservation(app, payload):
    partner = find_partner(
        app,
        slug=payload.get("partner_slug") or payload.get("slug"),
        codigo=payload.get("partner_code") or payload.get("codigo"),
        partner_id=payload.get("partner_id"),
        token=payload.get("booking_token"),
    )
    if not partner:
        raise ValueError("partner_not_found")
    if not partner.get("ativo", True) or str(partner.get("status", "Ativo")).lower() == "inativo":
        raise ValueError("partner_inactive")

    ref = str(payload.get("contributor_ref") or payload.get("ref") or payload.get("contributor_codigo") or "").strip()
    contributor = find_contributor(partner, ref)
    valor = _valor(payload)
    rede_pct = float(partner.get("comissao_percentual", partner.get("comissao_pct", partner.get("comissao_rede", 0))))
    sub_pct = float((contributor or {}).get("percentual_comissao", 0))
    comm = calc_commission(valor, rede_pct, sub_pct)

    treq_id = next_record_id("treq", getattr(app, "transport_requests", []))
    res_id = next_record_id("res", getattr(app, "reservations", []))
    numero = next_reservation_number(app)
    reservation_code = str(numero).lstrip("#")
    origem = str(payload.get("origem", "")).strip() or partner.get("nome_rede", "")
    destino = str(payload.get("destino", "")).strip()

    attr = {
        "partner_id": partner.get("id"),
        "partner_nome": partner.get("nome_rede"),
        "partner_slug": partner.get("slug"),
        "partner_code": partner.get("codigo", partner.get("codigo_acesso")),
        "contributor_id": (contributor or {}).get("id", ""),
        "contributor_nome": (contributor or {}).get("nome", ""),
        "contributor_code": (contributor or {}).get("codigo_ref", ""),
        "contributor_ref": (contributor or {}).get("codigo_ref", ""),
        "comissao_percentual": rede_pct,
        "subcomissao_percentual": sub_pct,
        "source": str(payload.get("source", SOURCE)),
        "flow": str(payload.get("flow", FLOW)),
        "canal_origem": "qr" if payload.get("via_qr") else ("link_contribuidor" if ref else "link"),
        "via_qr": bool(payload.get("via_qr")),
    }

    treq = {
        "id": treq_id,
        "origem": origem,
        "destino": destino,
        "data": str(payload.get("data", "")),
        "hora": str(payload.get("hora", "")),
        "nome": str(payload.get("nome", "")),
        "telefone": str(payload.get("telefone", payload.get("whatsapp", ""))),
        "email": str(payload.get("email", "")),
        "empresa": partner.get("nome_rede"),
        "passageiros": str(payload.get("passageiros", "1")),
        "bagagens": str(payload.get("bagagens", "0")),
        "veiculo_categoria": str(payload.get("veiculo_categoria", payload.get("categoria", ""))),
        "valor_estimado": valor,
        "status": "Recebida",
        "observacoes": str(payload.get("observacoes", "")),
        "origem_fonte": "Motor de Reservas",
        **attr,
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    if not hasattr(app, "transport_requests"):
        app.transport_requests = []
    app.transport_requests.insert(0, treq)

    reservation = {
        "numero": numero,
        "id": res_id,
        "cliente": treq["nome"] or partner.get("nome_rede"),
        "contato": treq["telefone"],
        "email": treq["email"],
        "tipo": treq.get("tipo_viagem", payload.get("tipo_viagem", "Transfer")),
        "trajeto": f"{origem} → {destino}".strip(" →"),
        "data": f'{treq["data"]} {treq["hora"]}'.strip(),
        "motorista": "",
        "valor": f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "status": "Pendente",
        "transport_request_id": treq_id,
        **attr,
        "criado_em": _now(),
    }
    if not hasattr(app, "reservations"):
        app.reservations = []
    app.reservations.insert(0, reservation)

    net_com = {
        "id": f"ncom-{res_id}",
        "uuid": str(uuid.uuid4()),
        "partner_id": partner.get("id"),
        "reservation_id": res_id,
        "reservation_numero": numero,
        "valor_base": valor,
        "percentual": rede_pct,
        "valor_bruto": comm["comissao_rede_bruta"],
        "valor_comissao": comm["comissao_rede_liquida"],
        "status_pagamento": "pendente",
        "created_at": _iso(),
    }
    if not hasattr(app, "network_commissions"):
        app.network_commissions = []
    app.network_commissions.insert(0, net_com)

    ccom = None
    if contributor and comm["comissao_contribuidor"] > 0:
        ccom = {
            "id": f"ccom-{res_id}",
            "uuid": str(uuid.uuid4()),
            "contributor_id": contributor.get("id"),
            "partner_id": partner.get("id"),
            "reservation_id": res_id,
            "percentual": sub_pct,
            "valor_comissao": comm["comissao_contribuidor"],
            "status_pagamento": "pendente",
            "created_at": _iso(),
        }
        if not hasattr(app, "contributor_commissions"):
            app.contributor_commissions = []
        app.contributor_commissions.insert(0, ccom)

    audit = write_audit(
        app,
        "network.reservation.created",
        partner.get("id"),
        {**attr, "reservation_id": res_id, "numero": numero, "reservation_code": reservation_code},
    )
    event = log_event(
        app,
        "reservation.created",
        f"Reserva rede {numero}",
        referencia_id=res_id,
        origem=SOURCE,
        payload=attr,
    )
    sync_partner_state(app)

    supabase_result = {"ok": True}
    try:
        from .repository.app_repository import AppRepository

        if AppRepository.BACKEND == "supabase":
            from .repository.supabase_store import persist_network_reservation_bundle

            supabase_result = persist_network_reservation_bundle(
                app,
                treq=treq,
                reservation=reservation,
                net_com=net_com,
                ccom=ccom,
                audit=audit,
                event=event,
            )
        else:
            from .repository.supabase_sync import sync_network_reservation

            supabase_result = sync_network_reservation(
                app,
                partner=partner,
                contributor=contributor,
                treq=treq,
                reservation=reservation,
                net_com=net_com,
                ccom=ccom,
                audit=audit,
            )
    except Exception as exc:
        supabase_result = {"ok": False, "error": str(exc)}

    from .storage import backup_state_keys

    backup_state_keys(
        app,
        (
            "transport_requests",
            "reservations",
            "network_commissions",
            "contributor_commissions",
            "audit_log",
            "event_log",
        ),
    )

    return {
        "ok": True,
        "reservation_id": res_id,
        "reservation_numero": numero,
        "reservation_code": reservation_code,
        "transport_request_id": treq_id,
        "supabase": supabase_result,
        **attr,
        **comm,
    }
