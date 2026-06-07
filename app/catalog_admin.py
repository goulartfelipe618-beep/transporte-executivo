"""Administracao master de hoteis, aeroportos e networks."""
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from .catalog import (
    HOTEL_CATEGORIES,
    NETWORK_TYPES,
    PUBLISH_STATUSES,
    normalize_airport,
    normalize_hotel,
    normalize_network,
    next_record_id,
)
from .components import resolve_widget_value
from .full_features import scrollable_form, settings_field, settings_section
from .theme import COLORS, FONTS, panel_frame, styled_button


def render_hotels(parent, app):
    _render_catalog_page(parent, app, "HOTEIS", "hotels", "Rede de Hoteis", normalize_hotel, "htl", _hotel_form)


def render_airports(parent, app):
    _render_catalog_page(parent, app, "AEROPORTOS", "airports", "Rede de Aeroportos", normalize_airport, "apt", _airport_form)


def render_networks(parent, app):
    _render_catalog_page(parent, app, "NETWORKS", "networks", "Networks / Parceiros", normalize_network, "net", _network_form)


def _render_catalog_page(parent, app, page_key, collection, title, normalizer, prefix, form_builder):
    if not hasattr(app, collection):
        setattr(app, collection, [])
    records = getattr(app, collection)

    parent.configure(bg=COLORS["bg"])
    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text=title, bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(title_box, text="Cadastro administrativo master. Somente registros publicados aparecem no Portal da Empresa.", bg=COLORS["bg"], fg=COLORS["muted"], font=FONTS["small"], wraplength=760, justify="left").pack(anchor="w", pady=(2, 0))
    styled_button(header, "+ Novo registro", style="success", command=lambda: _open_form(app, page_key, collection, normalizer, prefix, form_builder)).pack(side="right", anchor="n")

    box = panel_frame(parent)
    box.pack(fill="both", expand=True)
    columns = form_builder.columns
    tree = ttk.Treeview(box, columns=[c[0] for c in columns], show="headings", style="Custom.Treeview", height=14)
    for key, label, width in columns:
        tree.heading(key, text=label)
        tree.column(key, width=width, anchor="w")
    for item in records:
        tree.insert("", "end", iid=item.get("id"), values=tuple(item.get(key, "") for key, _, _ in columns))
    y_scroll = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=y_scroll.set)
    tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    y_scroll.pack(side="right", fill="y", pady=10)

    actions = tk.Frame(parent, bg=COLORS["bg"])
    actions.pack(fill="x", pady=8)
    styled_button(actions, "Editar", style="outline_primary", size="sm", command=lambda: _open_form(app, page_key, collection, normalizer, prefix, form_builder, _selected(tree, records))).pack(side="left", padx=(0, 6))
    styled_button(actions, "Excluir", style="outline_danger", size="sm", command=lambda: _delete(app, page_key, collection, tree, records)).pack(side="left")


def _selected(tree, records):
    selection = tree.selection()
    if not selection:
        return None
    return next((item for item in records if item.get("id") == selection[0]), None)


def _delete(app, page_key, collection, tree, records):
    item = _selected(tree, records)
    if not item:
        messagebox.showwarning("Excluir", "Selecione um registro.", parent=app)
        return
    if not messagebox.askyesno("Excluir", f'Excluir "{item.get("nome", "")}"?', parent=app):
        return
    updated = [row for row in records if row.get("id") != item.get("id")]
    setattr(app, collection, updated)
    app.save_state()
    app.show_page(page_key)


def _open_form(app, page_key, collection, normalizer, prefix, form_builder, record=None):
    window = tk.Toplevel(app)
    window.title("Editar registro" if record else "Novo registro")
    window.configure(bg=COLORS["bg"])
    window.geometry("640x620")
    window.transient(app)
    window.grab_set()
    form, _canvas = scrollable_form(window)
    fields = {}
    form_builder.build(form, fields, record)
    footer = tk.Frame(window, bg=COLORS["bg"])
    footer.pack(fill="x", padx=12, pady=12)
    styled_button(footer, "Cancelar", style="secondary", command=window.destroy).pack(side="right", padx=(8, 0))
    styled_button(footer, "Salvar", style="success", command=lambda: _save(app, window, page_key, collection, normalizer, prefix, fields, record)).pack(side="right")


def _save(app, window, page_key, collection, normalizer, prefix, fields, record):
    values = {}
    for key, widget in fields.items():
        if isinstance(widget, ttk.Combobox):
            values[key] = widget.get()
        elif isinstance(widget, tk.Text):
            values[key] = widget.get("1.0", "end-1c").strip()
        else:
            values[key] = resolve_widget_value(widget)
    if not values.get("nome"):
        messagebox.showwarning("Validacao", "Informe o nome.", parent=window)
        return
    records = getattr(app, collection)
    payload = normalizer({**(record or {}), **values, "id": (record or {}).get("id") or next_record_id(prefix, records), "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M")})
    updated = False
    for index, row in enumerate(records):
        if row.get("id") == payload.get("id"):
            records[index] = payload
            updated = True
            break
    if not updated:
        records.append(payload)
    setattr(app, collection, records)
    app.save_state()
    window.destroy()
    app.show_page(page_key)


class _FormSpec:
    def __init__(self, columns, build):
        self.columns = columns
        self.build = build


def _status_combo(parent, fields, record):
    box = tk.Frame(parent, bg=COLORS["panel"])
    box.pack(fill="x", padx=14, pady=4)
    tk.Label(box, text="Status", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
    widget = ttk.Combobox(box, values=PUBLISH_STATUSES, state="readonly")
    widget.set((record or {}).get("status", "Publicado"))
    widget.pack(fill="x", pady=(3, 0))
    fields["status"] = widget


def _hotel_form_build(form, fields, record):
    settings_section(form, "Hotel", "Rede administrativa de hoteis parceiros")
    panel = tk.Frame(form, bg=COLORS["panel"])
    panel.pack(fill="x")
    data = record or {}
    for key, label, ph, req in [
        ("nome", "Nome", "Nome do hotel", True),
        ("cidade", "Cidade", "Cidade", False),
        ("estado", "Estado (UF)", "UF", False),
        ("endereco", "Endereco", "Endereco completo", False),
        ("contato", "Contato", "Telefone ou email", False),
        ("observacoes", "Observacoes", "Observacoes", False),
    ]:
        settings_field(panel, fields, key, label, data.get(key, ""), ph, req)
    box = tk.Frame(panel, bg=COLORS["panel"])
    box.pack(fill="x", padx=14, pady=4)
    tk.Label(box, text="Categoria", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
    combo = ttk.Combobox(box, values=HOTEL_CATEGORIES, state="readonly")
    combo.set(data.get("categoria", "Executivo"))
    combo.pack(fill="x", pady=(3, 0))
    fields["categoria"] = combo
    _status_combo(panel, fields, record)


def _airport_form_build(form, fields, record):
    settings_section(form, "Aeroporto", "Rede administrativa de aeroportos")
    panel = tk.Frame(form, bg=COLORS["panel"])
    panel.pack(fill="x")
    data = record or {}
    for key, label, ph, req in [
        ("nome", "Nome", "Nome do aeroporto", True),
        ("cidade", "Cidade", "Cidade", False),
        ("estado", "Estado (UF)", "UF", False),
        ("codigo_iata", "Codigo IATA", "GRU", False),
        ("observacoes", "Observacoes", "Observacoes", False),
    ]:
        settings_field(panel, fields, key, label, data.get(key, ""), ph, req)
    _status_combo(panel, fields, record)


def _network_form_build(form, fields, record):
    settings_section(form, "Network", "Parceiros corporativos e operadores")
    panel = tk.Frame(form, bg=COLORS["panel"])
    panel.pack(fill="x")
    data = record or {}
    for key, label, ph, req in [
        ("nome", "Nome", "Nome do parceiro", True),
        ("cidade", "Cidade", "Cidade", False),
        ("estado", "Estado (UF)", "UF", False),
        ("contato", "Contato", "Contato", False),
        ("observacoes", "Observacoes", "Observacoes", False),
    ]:
        settings_field(panel, fields, key, label, data.get(key, ""), ph, req)
    box = tk.Frame(panel, bg=COLORS["panel"])
    box.pack(fill="x", padx=14, pady=4)
    tk.Label(box, text="Tipo", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
    combo = ttk.Combobox(box, values=NETWORK_TYPES, state="readonly")
    combo.set(data.get("tipo", "Parceiro Corporativo"))
    combo.pack(fill="x", pady=(3, 0))
    fields["tipo"] = combo
    _status_combo(panel, fields, record)


_hotel_form = _FormSpec(
    [
        ("nome", "Nome", 180),
        ("cidade", "Cidade", 120),
        ("estado", "UF", 50),
        ("categoria", "Categoria", 100),
        ("contato", "Contato", 120),
        ("status", "Status", 90),
    ],
    _hotel_form_build,
)
_airport_form = _FormSpec(
    [
        ("nome", "Nome", 180),
        ("codigo_iata", "IATA", 70),
        ("cidade", "Cidade", 120),
        ("estado", "UF", 50),
        ("status", "Status", 90),
    ],
    _airport_form_build,
)
_network_form = _FormSpec(
    [
        ("nome", "Nome", 180),
        ("tipo", "Tipo", 140),
        ("cidade", "Cidade", 120),
        ("estado", "UF", 50),
        ("status", "Status", 90),
    ],
    _network_form_build,
)
