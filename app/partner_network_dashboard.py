"""Dashboard da Rede Comercial — KPIs e visao executiva."""
from __future__ import annotations

from datetime import datetime

import tkinter as tk

from .components import summary_cards
from .partner_network import ensure_partner_networks
from .rede_solicitacoes_ui import network_transport_requests
from .theme import COLORS, FONTS, panel_frame, styled_button


def _parse_br_datetime(value):
    raw = str(value or "").strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            size = 16 if "%H" in fmt else 10
            return datetime.strptime(raw[:size], fmt)
        except ValueError:
            continue
    return None


def _network_kpis(app):
    ensure_partner_networks(app)
    requests = network_transport_requests(app)
    reservations = [
        r
        for r in getattr(app, "reservations", [])
        if r.get("source") == "network" or r.get("partner_id") or r.get("flow") == "express"
    ]
    today = datetime.now().date()
    month = today.month
    year = today.year
    today_count = 0
    month_count = 0
    for item in requests:
        when = _parse_br_datetime(item.get("criado_em")) or _parse_br_datetime(item.get("data"))
        if not when:
            continue
        if when.date() == today:
            today_count += 1
        if when.month == month and when.year == year:
            month_count += 1
    converted = sum(
        1
        for r in reservations
        if str(r.get("status", "")).lower() not in {"cancelada", "cancelado"}
    )
    total_req = len(requests)
    taxa = f"{(converted / total_req * 100):.1f}%" if total_req else "0%"
    partners_active = sum(1 for p in app.partner_networks if p.get("ativo", True))
    commissions = len(getattr(app, "network_commissions", []))
    return {
        "today": today_count,
        "month": month_count,
        "converted": converted,
        "rate": taxa,
        "partners": len(app.partner_networks),
        "partners_active": partners_active,
        "commissions": commissions,
        "requests": total_req,
    }


def render_rede_dashboard(parent, app):
    parent.configure(bg=COLORS["bg"])
    kpis = _network_kpis(app)

    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Dashboard da Rede Comercial", bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(
        title_box,
        text="Indicadores de solicitacoes do Motor, conversao e parceiros ativos.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
    ).pack(anchor="w", pady=(2, 0))
    styled_button(header, "Atualizar", style="secondary", command=lambda: app.show_page("REDE_DASHBOARD")).pack(side="right")

    row1 = tk.Frame(parent, bg=COLORS["bg"])
    row1.pack(fill="x", pady=(0, 8))
    summary_cards(
        row1,
        [
            {"label": "Solicitacoes hoje", "value": str(kpis["today"]), "hint": "Motor / Rede"},
            {"label": "Solicitacoes mes", "value": str(kpis["month"]), "hint": "Mes corrente"},
            {"label": "Reservas convertidas", "value": str(kpis["converted"]), "hint": "source=network"},
            {"label": "Taxa de conversao", "value": kpis["rate"], "hint": "Reservas / solicitacoes"},
        ],
    )

    row2 = tk.Frame(parent, bg=COLORS["bg"])
    row2.pack(fill="x", pady=(0, 12))
    summary_cards(
        row2,
        [
            {"label": "Parceiros cadastrados", "value": str(kpis["partners"]), "hint": f'{kpis["partners_active"]} ativos'},
            {"label": "Solicitacoes total", "value": str(kpis["requests"]), "hint": "Historico rede"},
            {"label": "Comissoes geradas", "value": str(kpis["commissions"]), "hint": "network_commissions"},
            {"label": "Gateway", "value": "8770", "hint": "/api/v1/network/*"},
        ],
    )

    panel = panel_frame(parent)
    panel.pack(fill="both", expand=True)
    tk.Label(
        panel,
        text="Fonte oficial: Sistema Master (partner_networks + transport_requests + reservations).",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=900,
        justify="left",
    ).pack(anchor="w", padx=16, pady=16)
    tk.Label(
        panel,
        text="Use REDE > Solicitacoes para a fila detalhada de pedidos do Motor.",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=FONTS["body"],
    ).pack(anchor="w", padx=16, pady=(0, 16))
    styled_button(panel, "Ver solicitacoes", style="primary", command=lambda: app.show_page("REDE_SOLICITACOES")).pack(anchor="w", padx=16, pady=(0, 16))
