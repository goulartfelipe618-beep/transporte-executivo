"""REDE > SOLICITACOES — pedidos originados pelo Motor de Reservas."""
from __future__ import annotations

from datetime import datetime
from tkinter import messagebox

import tkinter as tk

from .components import summary_cards
from .partner_network import ensure_partner_networks
from .table_ui import grid_table_cell, grid_table_header, render_action_buttons, table_scroll_host
from .theme import COLORS, FONTS, styled_button


def _parse_br_datetime(value):
    raw = str(value or "").strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            size = 16 if "%H" in fmt else 10
            return datetime.strptime(raw[:size], fmt)
        except ValueError:
            continue
    return None


def network_transport_requests(app):
    ensure_partner_networks(app)
    items = []
    for item in getattr(app, "transport_requests", []):
        if not isinstance(item, dict):
            continue
        if (
            item.get("source") == "network"
            or item.get("flow") == "express"
            or item.get("partner_id")
            or item.get("origem_fonte") == "Motor de Reservas"
        ):
            items.append(item)
    return items


def _reservation_for_request(app, treq_id):
    for res in getattr(app, "reservations", []):
        if res.get("transport_request_id") == treq_id:
            return res
    return None


def _valor_display(item, reservation=None):
    if reservation and reservation.get("valor"):
        return reservation.get("valor")
    raw = item.get("valor_estimado")
    if isinstance(raw, (int, float)) and raw:
        return f"R$ {raw:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "-"


def render_rede_solicitacoes(parent, app):
    parent.configure(bg=COLORS["bg"])
    requests = network_transport_requests(app)

    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 10))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Solicitacoes da Rede", bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(
        title_box,
        text="Pedidos recebidos pelo Motor de Reservas (source=network, flow=express).",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
    ).pack(anchor="w", pady=(2, 0))
    styled_button(header, "Atualizar", style="secondary", command=lambda: app.show_page("REDE_SOLICITACOES")).pack(side="right")

    today = datetime.now().date()
    month, year = today.month, today.year
    today_count = month_count = converted = 0
    for item in requests:
        when = _parse_br_datetime(item.get("criado_em")) or _parse_br_datetime(item.get("data"))
        if when:
            if when.date() == today:
                today_count += 1
            if when.month == month and when.year == year:
                month_count += 1
        res = _reservation_for_request(app, item.get("id"))
        if res and str(res.get("status", "")).lower() not in {"cancelada", "cancelado"}:
            converted += 1
    total = len(requests)
    taxa = f"{(converted / total * 100):.1f}%" if total else "0%"

    cards = tk.Frame(parent, bg=COLORS["bg"])
    cards.pack(fill="x", pady=(0, 10))
    summary_cards(
        cards,
        [
            {"label": "Solicitacoes hoje", "value": str(today_count), "hint": "Motor / Rede"},
            {"label": "Solicitacoes mes", "value": str(month_count), "hint": f"{month:02d}/{year}"},
            {"label": "Reservas convertidas", "value": str(converted), "hint": "Com reserva vinculada"},
            {"label": "Taxa de conversao", "value": taxa, "hint": "Reservas / solicitacoes"},
        ],
    )

    if not requests:
        box = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
        box.pack(fill="both", expand=True)
        tk.Label(
            box,
            text="Nenhuma solicitacao da rede ainda.\nUse o Motor com POST /api/v1/network/{slug}/{codigo}/reserve.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["body"],
            justify="center",
        ).pack(pady=60)
        return

    _, table = table_scroll_host(parent)
    weights = [1, 1, 2, 2, 2, 2, 2, 2, 1, 1, 0]
    headers = ["Numero", "Data", "Rede", "Contribuidor", "Passageiro", "Telefone", "Origem", "Destino", "Valor", "Status", "Acoes"]
    grid_table_header(table, headers, weights, [80, 90, 0, 0, 0, 0, 0, 0, 0, 70, 200])

    for row_index, item in enumerate(requests, start=1):
        bg = COLORS["panel"] if row_index % 2 else COLORS["panel_alt"]
        res = _reservation_for_request(app, item.get("id"))
        numero = (res or {}).get("numero") or item.get("id", "")
        when = " ".join(p for p in [item.get("data", ""), item.get("hora", "")] if p).strip() or item.get("criado_em", "-")
        values = [
            numero, when,
            item.get("partner_nome") or item.get("empresa", "-"),
            item.get("contributor_nome") or item.get("contributor_ref") or "-",
            item.get("nome", "-"), item.get("telefone", "-"),
            item.get("origem", "-"), item.get("destino", "-"),
            _valor_display(item, res),
            (res or {}).get("status") or item.get("status", "-"),
        ]
        for col, value in enumerate(values):
            grid_table_cell(table, row_index, col, value, bg, truncate=[None, 14, 20, 16, 18, 14, 22, 22, None, None][col])

        actions = tk.Frame(table, bg=bg)
        actions.grid(row=row_index, column=10, sticky="ew", padx=4, pady=4)
        render_action_buttons(
            actions,
            [
                ("Ver", lambda req=item, r=res: _show_details(app, req, r)),
                ("Reserva", lambda r=res: app.show_page("RESERVAS") if r else None, "primary"),
            ],
            bg=bg,
        )


def _show_details(app, request, reservation):
    lines = [
        f"Solicitacao: {request.get('id', '')}",
        f"Rede: {request.get('partner_nome', '')} ({request.get('partner_slug', '')})",
        f"Contribuidor: {request.get('contributor_nome', '-') or request.get('contributor_ref', '-')}",
        f"Passageiro: {request.get('nome', '')}",
        f"Telefone: {request.get('telefone', '')}",
        f"Origem: {request.get('origem', '')}",
        f"Destino: {request.get('destino', '')}",
        f"Data/Hora: {request.get('data', '')} {request.get('hora', '')}".strip(),
        f"Status solicitacao: {request.get('status', '')}",
    ]
    if reservation:
        lines.extend(["", f"Reserva: {reservation.get('numero', '')} ({reservation.get('id', '')})", f"Valor: {reservation.get('valor', '')}"])
    messagebox.showinfo("Solicitacao da Rede", "\n".join(lines), parent=app)
