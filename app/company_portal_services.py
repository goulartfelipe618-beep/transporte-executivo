"""Servicos e DTOs do Portal Empresa."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime

from .company_model import (
    append_portal_activity,
    company_reservations,
    company_transport_requests,
    find_company_user,
    normalize_cost_center,
    normalize_company_user,
    normalize_passenger,
)

APPROVAL_PROFILES = {"Gestor", "Administrador da Empresa"}
OPEN_STATUSES = {"pendente", "recebida", "aguardando aprovacao", "em analise", "confirmada", "agendada"}
IN_PROGRESS_STATUSES = {"em deslocamento", "em atendimento", "em andamento", "aprovada"}
DONE_STATUSES = {"concluida", "concluído", "concluido", "finalizada"}
CANCEL_STATUSES = {"cancelada", "cancelado", "rejeitada"}


def _status_bucket(status):
    value = str(status or "").strip().lower()
    if value in CANCEL_STATUSES:
        return "cancelled"
    if value in DONE_STATUSES:
        return "done"
    if value in IN_PROGRESS_STATUSES:
        return "in_progress"
    if value in OPEN_STATUSES or value:
        return "open"
    return "open"


def _parse_date(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:16] if " " in raw and fmt == "%d/%m/%Y %H:%M" else raw[:10], fmt)
        except ValueError:
            continue
    return None


def _parse_money(value):
    raw = str(value or "").replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.0


def reservation_dto(reservation):
    return {
        "numero": reservation.get("numero"),
        "cliente": reservation.get("cliente"),
        "data": reservation.get("data"),
        "trajeto": reservation.get("trajeto"),
        "status": reservation.get("status"),
        "centro_custo_id": reservation.get("centro_custo_id", ""),
        "centro_custo_nome": reservation.get("centro_custo_nome", ""),
        "transport_request_id": reservation.get("transport_request_id", ""),
        "criado_em": reservation.get("criado_em", reservation.get("data", "")),
    }


def request_dto(request):
    return {
        "id": request.get("id"),
        "origem": request.get("origem"),
        "destino": request.get("destino"),
        "data": request.get("data"),
        "hora": request.get("hora"),
        "status": request.get("status"),
        "categoria": request.get("categoria"),
        "passageiros": request.get("passageiros"),
        "centro_custo_id": request.get("centro_custo_id", ""),
        "centro_custo_nome": request.get("centro_custo_nome", ""),
        "approval_status": request.get("approval_status", request.get("status", "")),
        "criado_em": request.get("criado_em"),
    }


def dashboard_payload(app, company):
    reservations = company_reservations(app, company)
    requests = company_transport_requests(app, company)
    buckets = {"open": 0, "in_progress": 0, "done": 0, "cancelled": 0}
    for item in reservations + requests:
        buckets[_status_bucket(item.get("status"))] += 1
    activity = []
    for row in (company.get("portal_activity") or [])[:8]:
        activity.append(f'{row.get("titulo", "")} — {row.get("resumo", "")} ({row.get("criado_em", "")})')
    if not activity:
        for item in (requests[:3] + reservations[:3]):
            label = item.get("id") or item.get("numero") or "movimentacao"
            activity.append(f'{label} - {item.get("status", "")} - {item.get("criado_em") or item.get("data", "")}')
    last_activity = (company.get("portal_activity") or [{}])[0].get("criado_em", "")
    if not last_activity and activity:
        last_activity = activity[0].split(" - ")[-1]
    done = sum(1 for item in reservations if _status_bucket(item.get("status")) == "done")
    upcoming = sum(1 for item in reservations if _status_bucket(item.get("status")) in {"open", "in_progress"})
    pending_requests = sum(
        1
        for item in requests
        if str(item.get("status", "")).lower() in {"recebida", "em analise", "aguardando aprovacao"}
    )
    return {
        "company": {
            "nome": company.get("razao_social") or company.get("nome_fantasia", ""),
            "id": company.get("id", ""),
            "status_empresa": company.get("status_empresa", "Ativa"),
        },
        "stats": {
            "open": buckets["open"],
            "in_progress": buckets["in_progress"],
            "done": done,
            "cancelled": buckets["cancelled"],
            "upcoming": upcoming,
            "pending_requests": pending_requests,
            "last_activity": last_activity,
            "indicators": {
                "usuarios_ativos": sum(1 for u in company.get("usuarios") or [] if u.get("status") == "Ativo"),
                "centros_custo": len(company.get("centros_custo") or []),
                "passageiros": len(company.get("passageiros") or []),
            },
        },
        "activity": activity,
    }


def history_payload(app, company, *, status="", centro_custo_id="", date_from="", date_to="", page=1, per_page=20):
    reservations = [reservation_dto(r) for r in company_reservations(app, company)]
    requests = [request_dto(r) for r in company_transport_requests(app, company)]
    items = [{"tipo": "reserva", **row} for row in reservations] + [{"tipo": "solicitacao", **row} for row in requests]

    if status:
        status_lower = status.lower()
        items = [i for i in items if status_lower in str(i.get("status", "")).lower()]
    if centro_custo_id:
        items = [i for i in items if str(i.get("centro_custo_id", "")) == str(centro_custo_id)]

    if date_from or date_to:
        start = _parse_date(date_from)
        end = _parse_date(date_to)
        filtered = []
        for item in items:
            dt = _parse_date(item.get("data") or item.get("criado_em"))
            if not dt:
                continue
            if start and dt < start:
                continue
            if end and dt > end:
                continue
            filtered.append(item)
        items = filtered

    items.sort(key=lambda row: str(row.get("criado_em") or row.get("data") or ""), reverse=True)
    total = len(items)
    page = max(1, int(page or 1))
    per_page = max(5, min(100, int(per_page or 20)))
    start_idx = (page - 1) * per_page
    page_items = items[start_idx : start_idx + per_page]
    return {"items": page_items, "total": total, "page": page, "per_page": per_page, "pages": max(1, (total + per_page - 1) // per_page)}


def user_dto(user):
    return {
        "id": user.get("id"),
        "nome": user.get("nome"),
        "email": user.get("email"),
        "telefone": user.get("telefone"),
        "perfil": user.get("perfil"),
        "status": user.get("status"),
        "criado_em": user.get("criado_em"),
    }


def list_users(company):
    return [user_dto(u) for u in company.get("usuarios") or []]


def save_user(company, payload, *, actor):
    users = list(company.get("usuarios") or [])
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise ValueError("email_obrigatorio")
    existing = find_company_user(company, email)
    if existing and str(existing.get("id")) != str(payload.get("id", "")):
        raise ValueError("email_duplicado")
    if payload.get("id"):
        updated = None
        for index, user in enumerate(users):
            if str(user.get("id")) == str(payload.get("id")):
                row = normalize_company_user({**user, **payload}, company.get("id"))
                if payload.get("senha"):
                    row["senha"] = payload["senha"]
                users[index] = row
                updated = row
                break
        if not updated:
            raise ValueError("usuario_nao_encontrado")
    else:
        row = normalize_company_user(payload, company.get("id"))
        users.append(row)
        updated = row
    company["usuarios"] = users
    append_portal_activity(company, "Usuario corporativo", f'{updated.get("email")} ({updated.get("perfil")})', user_id=actor.get("id", ""))
    return user_dto(updated)


def delete_user(company, user_id, *, actor):
    users = [u for u in company.get("usuarios") or [] if str(u.get("id")) != str(user_id)]
    if len(users) == len(company.get("usuarios") or []):
        raise ValueError("usuario_nao_encontrado")
    if str(actor.get("id", "")) == str(user_id):
        raise ValueError("nao_pode_excluir_a_si_mesmo")
    company["usuarios"] = users
    append_portal_activity(company, "Usuario removido", str(user_id), user_id=actor.get("id", ""))


def list_cost_centers(company):
    return list(company.get("centros_custo") or [])


def save_cost_center(company, payload, *, actor):
    centros = list(company.get("centros_custo") or [])
    if payload.get("id"):
        saved = None
        for index, item in enumerate(centros):
            if str(item.get("id")) == str(payload.get("id")):
                centros[index] = normalize_cost_center({**item, **payload}, company.get("id"), centros)
                saved = centros[index]
                break
        if not saved:
            raise ValueError("centro_nao_encontrado")
    else:
        saved = normalize_cost_center(payload, company.get("id"), centros)
        centros.append(saved)
    company["centros_custo"] = centros
    append_portal_activity(company, "Centro de custo", saved.get("nome", ""), user_id=actor.get("id", ""), referencia_id=saved.get("id", ""))
    return saved


def delete_cost_center(company, centro_id, *, actor):
    company["centros_custo"] = [c for c in company.get("centros_custo") or [] if str(c.get("id")) != str(centro_id)]
    append_portal_activity(company, "Centro de custo removido", str(centro_id), user_id=actor.get("id", ""))


def list_passengers(company):
    return list(company.get("passageiros") or [])


def save_passenger(company, payload, *, actor):
    items = list(company.get("passageiros") or [])
    if payload.get("id"):
        saved = None
        for index, item in enumerate(items):
            if str(item.get("id")) == str(payload.get("id")):
                items[index] = normalize_passenger({**item, **payload}, company.get("id"), items)
                saved = items[index]
                break
        if not saved:
            raise ValueError("passageiro_nao_encontrado")
    else:
        saved = normalize_passenger(payload, company.get("id"), items)
        items.append(saved)
    company["passageiros"] = items
    append_portal_activity(company, "Passageiro", saved.get("nome", ""), user_id=actor.get("id", ""), referencia_id=saved.get("id", ""))
    return saved


def delete_passenger(company, passenger_id, *, actor):
    company["passageiros"] = [p for p in company.get("passageiros") or [] if str(p.get("id")) != str(passenger_id)]
    append_portal_activity(company, "Passageiro removido", str(passenger_id), user_id=actor.get("id", ""))


def finance_payload(app, company, *, centro_custo_id="", date_from="", date_to=""):
    rows = []
    total = 0.0
    for reservation in company_reservations(app, company):
        if centro_custo_id and str(reservation.get("centro_custo_id", "")) != str(centro_custo_id):
            continue
        dt = _parse_date(reservation.get("data"))
        if date_from and dt and dt < _parse_date(date_from):
            continue
        if date_to and dt and dt > _parse_date(date_to):
            continue
        amount = _parse_money(reservation.get("valor"))
        total += amount
        rows.append(
            {
                "numero": reservation.get("numero"),
                "data": reservation.get("data"),
                "descricao": reservation.get("trajeto"),
                "centro_custo": reservation.get("centro_custo_nome", ""),
                "status": reservation.get("status"),
                "valor": reservation.get("valor") or f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            }
        )
    by_status = {}
    for row in rows:
        key = row.get("status") or "Outros"
        by_status[key] = by_status.get(key, 0) + _parse_money(row.get("valor"))
    return {"total": total, "total_fmt": f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "items": rows, "by_status": by_status}


def export_excel_csv(app, company, **filters):
    finance = finance_payload(app, company, **filters)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Numero", "Data", "Descricao", "Centro de Custo", "Status", "Valor"])
    for row in finance["items"]:
        writer.writerow([row["numero"], row["data"], row["descricao"], row["centro_custo"], row["status"], row["valor"]])
    return buffer.getvalue()


def export_pdf_html(app, company, **filters):
    finance = finance_payload(app, company, **filters)
    rows = "".join(
        f"<tr><td>{r['numero']}</td><td>{r['data']}</td><td>{r['descricao']}</td><td>{r['centro_custo']}</td><td>{r['status']}</td><td>{r['valor']}</td></tr>"
        for r in finance["items"]
    )
    company_name = company.get("razao_social") or company.get("nome_fantasia") or "Empresa"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Relatorio Financeiro</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;padding:24px}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #ddd;padding:8px;font-size:12px}}th{{background:#f5f5f5}}</style></head>
<body><h1>Relatorio Financeiro — {company_name}</h1><p>Total: {finance['total_fmt']}</p>
<table><thead><tr><th>Numero</th><th>Data</th><th>Descricao</th><th>Centro de Custo</th><th>Status</th><th>Valor</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""


def resolve_cost_center(company, centro_custo_id):
    for centro in company.get("centros_custo") or []:
        if str(centro.get("id")) == str(centro_custo_id):
            return centro
    return None


def needs_approval(user):
    return user.get("perfil") == "Solicitante"
