"""Visualizacao do log de eventos para auditoria futura."""
import tkinter as tk
from tkinter import messagebox, ttk

from .platform import EVENT_TYPES, ensure_platform_collections
from .theme import COLORS, FONTS, panel_frame, styled_button


def render_event_log(parent, app):
    ensure_platform_collections(app)
    parent.configure(bg=COLORS["bg"])

    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Log de Eventos", bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(
        title_box,
        text="Auditoria preparatoria de cadastros recebidos, conversoes e acoes operacionais da plataforma.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=760,
        justify="left",
    ).pack(anchor="w", pady=(2, 0))
    styled_button(header, "Atualizar", style="secondary", command=lambda: render_event_log(parent, app)).pack(side="right", anchor="n")

    cards = tk.Frame(parent, bg=COLORS["bg"])
    cards.pack(fill="x", pady=(0, 12))
    site_events = sum(1 for item in app.event_log if item.get("origem") == "Site")
    _metric_card(cards, "Eventos registrados", str(len(app.event_log)), "historico local").pack(side="left", fill="x", expand=True, padx=(0, 8))
    _metric_card(cards, "Origem Site", str(site_events), "preparado para webhook").pack(side="left", fill="x", expand=True, padx=(0, 8))
    _metric_card(cards, "Tipos monitorados", str(len(EVENT_TYPES)), "eventos padronizados").pack(side="left", fill="x", expand=True)

    box = panel_frame(parent)
    box.pack(fill="both", expand=True)
    columns = ("criado_em", "tipo", "titulo", "resumo", "origem", "referencia_id")
    tree = ttk.Treeview(box, columns=columns, show="headings", style="Custom.Treeview", height=16)
    headings = [
        ("criado_em", "Data/Hora", 130),
        ("tipo", "Tipo", 180),
        ("titulo", "Titulo", 180),
        ("resumo", "Resumo", 260),
        ("origem", "Origem", 90),
        ("referencia_id", "Referencia", 110),
    ]
    for key, label, width in headings:
        tree.heading(key, text=label)
        tree.column(key, width=width, anchor="w")
    for item in app.event_log:
        tree.insert(
            "",
            "end",
            iid=item.get("id"),
            values=tuple(item.get(key, "") for key, _, _ in headings),
        )
    y_scroll = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=y_scroll.set)
    tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    y_scroll.pack(side="right", fill="y", pady=10)

    actions = tk.Frame(parent, bg=COLORS["bg"])
    actions.pack(fill="x", pady=8)
    styled_button(actions, "Detalhes", style="outline_primary", size="sm", command=lambda: _show_event(app, tree)).pack(side="left")


def _metric_card(parent, title, value, hint):
    card = panel_frame(parent)
    tk.Label(card, text=title, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(10, 0))
    tk.Label(card, text=value, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=12)
    tk.Label(card, text=hint, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(0, 10))
    return card


def _show_event(app, tree):
    selection = tree.selection()
    if not selection:
        messagebox.showwarning("Log de eventos", "Selecione um evento.", parent=app)
        return
    event = next((item for item in app.event_log if item.get("id") == selection[0]), None)
    if not event:
        return
    payload = event.get("payload") or {}
    payload_text = "\n".join(f"  {key}: {value}" for key, value in payload.items()) if payload else "  (sem payload)"
    messagebox.showinfo(
        "Detalhes do evento",
        "\n".join(
            [
                f"ID: {event.get('id', '')}",
                f"Tipo: {event.get('tipo', '')}",
                f"Titulo: {event.get('titulo', '')}",
                f"Resumo: {event.get('resumo', '')}",
                f"Origem: {event.get('origem', '')}",
                f"Referencia: {event.get('referencia_id', '')}",
                f"Criado em: {event.get('criado_em', '')}",
                "Payload:",
                payload_text,
            ]
        ),
        parent=app,
    )
