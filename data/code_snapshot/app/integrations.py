"""Armazenamento e administracao de integracoes preparatorias."""
import json
import os

import tkinter as tk
from tkinter import messagebox, ttk

from .components import resolve_widget_value, setup_placeholder
from .platform import (
    DEFAULT_INTEGRATIONS,
    INTEGRATION_STATUSES,
    INTEGRATION_TYPES,
    log_event,
    next_record_id,
    normalize_integration,
)
from .theme import COLORS, FONTS, panel_frame, styled_button

INTEGRATIONS_FILE = os.path.join("data", "integrations.json")


def ensure_integrations_loaded(app):
    if hasattr(app, "integrations"):
        app.integrations = [normalize_integration(item) for item in app.integrations]
        return
    app.integrations = []
    if os.path.exists(INTEGRATIONS_FILE):
        try:
            with open(INTEGRATIONS_FILE, encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (json.JSONDecodeError, OSError):
            loaded = []
        app.integrations = [normalize_integration(item) for item in loaded]
    if not app.integrations:
        app.integrations = [normalize_integration(item) for item in DEFAULT_INTEGRATIONS]
        save_integrations(app)


def save_integrations(app):
    os.makedirs(os.path.dirname(INTEGRATIONS_FILE), exist_ok=True)
    app.integrations = [normalize_integration(item) for item in getattr(app, "integrations", [])]
    with open(INTEGRATIONS_FILE, "w", encoding="utf-8") as handle:
        json.dump(app.integrations, handle, ensure_ascii=False, indent=2)


def render_integrations(parent, app):
    ensure_integrations_loaded(app)
    parent.configure(bg=COLORS["bg"])

    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Integracoes", bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(
        title_box,
        text="Arquitetura preparatoria para conexao futura com o site publico. Nenhuma integracao real e executada nesta fase.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=760,
        justify="left",
    ).pack(anchor="w", pady=(2, 0))
    styled_button(header, "+ Nova integracao", style="success", command=lambda: open_integration_form(app)).pack(side="right", anchor="n")

    cards = tk.Frame(parent, bg=COLORS["bg"])
    cards.pack(fill="x", pady=(0, 12))
    active = sum(1 for item in app.integrations if item.get("status") == "Ativa")
    configured = sum(1 for item in app.integrations if item.get("status") == "Configuracao")
    _metric_card(cards, "Integracoes", str(len(app.integrations)), "cadastradas").pack(side="left", fill="x", expand=True, padx=(0, 8))
    _metric_card(cards, "Ativas", str(active), "prontas para uso futuro").pack(side="left", fill="x", expand=True, padx=(0, 8))
    _metric_card(cards, "Em configuracao", str(configured), "aguardando site").pack(side="left", fill="x", expand=True)

    box = panel_frame(parent)
    box.pack(fill="both", expand=True)
    columns = ("nome", "tipo", "endpoint", "status", "sync")
    tree = ttk.Treeview(box, columns=columns, show="headings", style="Custom.Treeview", height=14)
    for col, title, width in [
        ("nome", "Nome", 220),
        ("tipo", "Tipo", 110),
        ("endpoint", "Endpoint", 260),
        ("status", "Status", 110),
        ("sync", "Ultima sincronizacao", 150),
    ]:
        tree.heading(col, text=title)
        tree.column(col, width=width, anchor="w")
    for item in app.integrations:
        tree.insert(
            "",
            "end",
            iid=item.get("id"),
            values=(
                item.get("nome", ""),
                item.get("tipo", ""),
                item.get("endpoint", ""),
                item.get("status", ""),
                item.get("ultima_sincronizacao", "") or "-",
            ),
        )
    y_scroll = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=y_scroll.set)
    tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    y_scroll.pack(side="right", fill="y", pady=10)

    actions = tk.Frame(parent, bg=COLORS["bg"])
    actions.pack(fill="x", pady=8)
    styled_button(actions, "Editar", style="outline_primary", size="sm", command=lambda: _edit_selected(app, tree)).pack(side="left", padx=(0, 6))
    styled_button(actions, "Excluir", style="outline_danger", size="sm", command=lambda: _delete_selected(app, tree, parent)).pack(side="left")


def _metric_card(parent, title, value, hint):
    card = panel_frame(parent)
    tk.Label(card, text=title, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(10, 0))
    tk.Label(card, text=value, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=12)
    tk.Label(card, text=hint, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(0, 10))
    return card


def _selected_integration(app, tree):
    selection = tree.selection()
    if not selection:
        return None
    return next((item for item in app.integrations if item.get("id") == selection[0]), None)


def _edit_selected(app, tree):
    item = _selected_integration(app, tree)
    if not item:
        messagebox.showwarning("Integracoes", "Selecione uma integracao.", parent=app)
        return
    open_integration_form(app, item)


def _delete_selected(app, tree, parent):
    item = _selected_integration(app, tree)
    if not item:
        messagebox.showwarning("Integracoes", "Selecione uma integracao.", parent=app)
        return
    if not messagebox.askyesno("Excluir", f'Excluir integracao "{item.get("nome", "")}"?', parent=app):
        return
    app.integrations = [row for row in app.integrations if row.get("id") != item.get("id")]
    save_integrations(app)
    log_event(app, "integration.updated", f'Integracao removida: {item.get("nome", "")}', referencia_id=item.get("id", ""))
    app.save_state()
    app.show_page("INTEGRACOES")


def open_integration_form(app, integration=None):
    window = tk.Toplevel(app)
    editing = integration is not None
    window.title("Editar integracao" if editing else "Nova integracao")
    window.configure(bg=COLORS["bg"])
    window.geometry("620x520")
    window.transient(app)
    window.grab_set()

    shell = panel_frame(window)
    shell.pack(fill="both", expand=True, padx=14, pady=14)
    fields = {}
    tk.Label(shell, text="Integracao", bg=COLORS["panel"], fg=COLORS["primary"], font=FONTS["heading"]).pack(anchor="w", padx=14, pady=(12, 8))
    form = tk.Frame(shell, bg=COLORS["panel"])
    form.pack(fill="both", expand=True, padx=14)
    _field(form, fields, "nome", "Nome da integracao", integration.get("nome", "") if integration else "")
    _combo(form, fields, "tipo", "Tipo", INTEGRATION_TYPES, integration.get("tipo") if integration else "Webhook")
    _field(form, fields, "endpoint", "Endpoint", integration.get("endpoint", "") if integration else "", "Ex: /api/inbound/company-leads")
    _combo(form, fields, "status", "Status", INTEGRATION_STATUSES, integration.get("status") if integration else "Configuracao")
    _field(form, fields, "ultima_sincronizacao", "Ultima sincronizacao", integration.get("ultima_sincronizacao", "") if integration else "", "DD/MM/AAAA HH:MM")
    _text(form, fields, "observacoes", "Observacoes", integration.get("observacoes", "") if integration else "")

    footer = tk.Frame(shell, bg=COLORS["panel"])
    footer.pack(fill="x", padx=14, pady=12)
    styled_button(footer, "Cancelar", style="secondary", command=window.destroy).pack(side="right", padx=(8, 0))
    styled_button(footer, "Salvar", style="success", command=lambda: _save_integration(app, window, fields, integration)).pack(side="right")


def _field(parent, fields, key, label, value="", placeholder=""):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["small"]).pack(anchor="w", pady=(4, 2))
    entry = tk.Entry(parent, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=FONTS["body"])
    entry.pack(fill="x", ipady=6, pady=(0, 6))
    if value:
        entry.insert(0, value)
    elif placeholder:
        setup_placeholder(entry, placeholder)
    fields[key] = entry


def _combo(parent, fields, key, label, values, current):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["small"]).pack(anchor="w", pady=(4, 2))
    widget = ttk.Combobox(parent, values=values, state="readonly", font=FONTS["body"])
    widget.set(current or values[0])
    widget.pack(fill="x", pady=(0, 6))
    fields[key] = widget


def _text(parent, fields, key, label, value=""):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["small"]).pack(anchor="w", pady=(4, 2))
    widget = tk.Text(parent, height=3, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=FONTS["body"])
    widget.pack(fill="x", pady=(0, 6))
    if value:
        widget.insert("1.0", value)
    fields[key] = widget


def _save_integration(app, window, fields, integration):
    nome = resolve_widget_value(fields["nome"])
    if not nome:
        messagebox.showwarning("Integracoes", "Informe o nome da integracao.", parent=window)
        return
    payload = normalize_integration(
        {
            "id": integration.get("id") if integration else next_record_id("int", app.integrations),
            "nome": nome,
            "tipo": fields["tipo"].get(),
            "endpoint": resolve_widget_value(fields["endpoint"]),
            "status": fields["status"].get(),
            "ultima_sincronizacao": resolve_widget_value(fields["ultima_sincronizacao"]),
            "observacoes": fields["observacoes"].get("1.0", "end-1c").strip(),
            "criado_em": (integration or {}).get("criado_em"),
        }
    )
    updated = False
    for index, row in enumerate(app.integrations):
        if row.get("id") == payload.get("id"):
            app.integrations[index] = payload
            updated = True
            break
    if not updated:
        app.integrations.append(payload)
    save_integrations(app)
    log_event(app, "integration.updated", f'Integracao salva: {payload.get("nome", "")}', referencia_id=payload.get("id", ""))
    app.save_state()
    window.destroy()
    app.show_page("INTEGRACOES")
