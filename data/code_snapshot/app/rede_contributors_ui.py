"""Cadastro de contribuidores da Rede — ref tracking e subcomissao."""
from __future__ import annotations

from tkinter import messagebox, ttk

import tkinter as tk

from .components import resolve_widget_value
from .full_features import scrollable_form, settings_field, settings_section
from .partner_network import booking_url, normalize_contributor, sync_partner_state
from .table_ui import grid_table_cell, grid_table_header, render_action_buttons, table_scroll_host
from .theme import COLORS, FONTS, styled_button


def contributor_link(partner, contributor):
    base = booking_url(partner)
    ref = str(contributor.get("codigo_ref", "")).strip()
    if not base or not ref:
        return ""
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}ref={ref}"


def open_contributors_window(app, partner):
    window = tk.Toplevel(app)
    window.title(f"Contribuidores — {partner.get('nome_rede', partner.get('nome', ''))}")
    window.configure(bg=COLORS["bg"])
    window.geometry("760x520")
    window.minsize(640, 420)
    window.transient(app)
    window.grab_set()

    header = tk.Frame(window, bg=COLORS["bg"])
    header.pack(fill="x", padx=12, pady=(12, 8))
    tk.Label(
        header,
        text="Contribuidores rastreiam pedidos via ?ref=codigo_ref no link do Motor.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=700,
        justify="left",
    ).pack(side="left", fill="x", expand=True)
    styled_button(header, "+ Novo", style="success", command=lambda: _open_form(app, window, partner)).pack(side="right")

    _, table = table_scroll_host(window)
    weights = [2, 2, 1, 1, 0]
    headers = ["Nome", "Codigo ref", "Comissao %", "Status", "Acoes"]
    grid_table_header(table, headers, weights, [0, 0, 80, 70, 220])

    contributors = list(partner.get("contribuidores") or [])

    def refresh():
        for widget in table.winfo_children():
            if int(widget.grid_info().get("row", 0)) > 0:
                widget.destroy()
        for row_index, item in enumerate(contributors, start=1):
            _row(table, app, window, partner, contributors, item, row_index, refresh)

    if not contributors:
        empty = tk.Frame(table, bg=COLORS["panel"])
        empty.grid(row=1, column=0, columnspan=5, sticky="ew", padx=8, pady=24)
        tk.Label(empty, text="Nenhum contribuidor cadastrado.", bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["small"]).pack()
    else:
        refresh()


def _row(table, app, parent, partner, contributors, item, row_index, refresh):
    bg = COLORS["panel"] if row_index % 2 else COLORS["panel_alt"]
    status = "Ativo" if item.get("ativo", True) else "Inativo"
    for col, value in enumerate(
        [
            item.get("nome", ""),
            item.get("codigo_ref", ""),
            f'{item.get("percentual_comissao", 0):g}%',
            status,
        ]
    ):
        grid_table_cell(table, row_index, col, value, bg)
    actions = tk.Frame(table, bg=bg)
    actions.grid(row=row_index, column=4, sticky="ew", padx=4, pady=4)
    render_action_buttons(
        actions,
        [
            ("Editar", lambda: _open_form(app, parent, partner, item, refresh)),
            ("Link", lambda: _copy_link(app, partner, item)),
            ("Remover", lambda: _remove(app, partner, contributors, item, refresh), "danger"),
        ],
        bg=bg,
    )


def _open_form(app, parent, partner, contributor=None, refresh=None):
    win = tk.Toplevel(parent)
    win.title("Editar contribuidor" if contributor else "Novo contribuidor")
    win.configure(bg=COLORS["bg"])
    win.geometry("480x360")
    win.transient(parent)
    win.grab_set()

    form, _ = scrollable_form(win)
    fields = {}
    data = dict(contributor or {})
    panel = tk.Frame(form, bg=COLORS["panel"])
    panel.pack(fill="x")
    settings_section(form, "Contribuidor", "Nome e codigo de rastreamento (?ref=)")
    for key, label, ph, req in [
        ("nome", "Nome", "Ex.: Recepcionista Maria", True),
        ("codigo_ref", "Codigo ref", "Ex.: maria-recepcao", True),
        ("percentual_comissao", "Comissao sobre comissao rede (%)", "Ex.: 20", False),
    ]:
        settings_field(panel, fields, key, label, data.get(key, ""), ph, req)

    footer = tk.Frame(win, bg=COLORS["bg"])
    footer.pack(fill="x", padx=12, pady=12)
    styled_button(footer, "Cancelar", style="secondary", command=win.destroy).pack(side="right", padx=(8, 0))
    styled_button(
        footer,
        "Salvar",
        style="success",
        command=lambda: _save(app, win, partner, fields, contributor, refresh),
    ).pack(side="right")


def _save(app, window, partner, fields, contributor, refresh):
    values = {key: resolve_widget_value(widget) for key, widget in fields.items()}
    if not str(values.get("nome", "")).strip():
        messagebox.showwarning("Validacao", "Informe o nome.", parent=window)
        return
    if not str(values.get("codigo_ref", "")).strip():
        messagebox.showwarning("Validacao", "Informe o codigo ref.", parent=window)
        return

    siblings = list(partner.get("contribuidores") or [])
    saved = normalize_contributor({**(contributor or {}), **values}, partner.get("id"), siblings)
    updated = False
    for index, row in enumerate(siblings):
        if row.get("id") == saved.get("id"):
            siblings[index] = saved
            updated = True
            break
    if not updated:
        siblings.append(saved)

    for index, row in enumerate(app.partner_networks):
        if row.get("id") == partner.get("id"):
            app.partner_networks[index] = {**row, "contribuidores": siblings}
            break
    sync_partner_state(app)
    app.save_state()
    window.destroy()
    if refresh:
        refresh()
    messagebox.showinfo("Salvo", f'Contribuidor "{saved.get("nome")}" cadastrado.', parent=app)


def _copy_link(app, partner, contributor):
    link = contributor_link(partner, contributor)
    if not link:
        messagebox.showwarning("Link", "Salve o contribuidor com codigo ref valido.", parent=app)
        return
    app.clipboard_clear()
    app.clipboard_append(link)
    messagebox.showinfo("Link copiado", link, parent=app)


def _remove(app, partner, contributors, item, refresh):
    if not messagebox.askyesno("Remover", f'Remover "{item.get("nome", "")}"?', parent=app):
        return
    contributors[:] = [c for c in contributors if c.get("id") != item.get("id")]
    for index, row in enumerate(app.partner_networks):
        if row.get("id") == partner.get("id"):
            app.partner_networks[index] = {**row, "contribuidores": contributors}
            break
    sync_partner_state(app)
    app.save_state()
    refresh()
