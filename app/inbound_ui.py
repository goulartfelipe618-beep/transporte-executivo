"""Telas de entrada preparatorias: leads e solicitacoes do site."""
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from .components import resolve_widget_value, setup_placeholder
from .full_features import scrollable_form, settings_field, settings_section
from .platform import (
    COMPANY_LEAD_STATUSES,
    DRIVER_LEAD_STATUSES,
    ORIGIN_SITE,
    TRANSPORT_REQUEST_STATUSES,
    ensure_platform_collections,
    log_event,
    next_record_id,
    normalize_company_lead,
    normalize_driver_lead,
    normalize_transport_request,
)
from .theme import COLORS, FONTS, panel_frame, styled_button


def render_company_leads(parent, app):
    _render_inbound_page(
        parent,
        app,
        page_key="LEADS_EMPRESAS",
        title="Leads de Empresas",
        subtitle="Empresas interessadas recebidas pelo site. Estrutura preparatoria para integracao futura.",
        collection="company_leads",
        columns=[
            ("empresa", "Empresa", 180),
            ("responsavel", "Responsavel", 140),
            ("telefone", "Telefone", 110),
            ("email", "Email", 160),
            ("cidade", "Cidade", 110),
            ("estado", "UF", 50),
            ("status", "Status", 120),
        ],
        normalizer=normalize_company_lead,
        id_prefix="clead",
        event_received="site.company_lead.received",
        form_builder=_company_lead_form,
        statuses=COMPANY_LEAD_STATUSES,
    )


def render_driver_leads(parent, app):
    _render_inbound_page(
        parent,
        app,
        page_key="LEADS_MOTORISTAS",
        title="Leads de Motoristas",
        subtitle="Motoristas interessados recebidos pelo site. Estrutura preparatoria para integracao futura.",
        collection="driver_leads",
        columns=[
            ("nome", "Nome", 160),
            ("telefone", "Telefone", 110),
            ("whatsapp", "WhatsApp", 110),
            ("email", "Email", 150),
            ("cidade", "Cidade", 110),
            ("estado", "UF", 50),
            ("categoria", "Categoria", 90),
            ("status", "Status", 120),
        ],
        normalizer=normalize_driver_lead,
        id_prefix="dlead",
        event_received="site.driver_lead.received",
        form_builder=_driver_lead_form,
        statuses=DRIVER_LEAD_STATUSES,
    )


def render_transport_requests(parent, app):
    _render_inbound_page(
        parent,
        app,
        page_key="SOLICITACOES",
        title="Solicitacoes de Transporte",
        subtitle="Pedidos recebidos pelo site publico. Estrutura preparatoria para triagem e conversao em reservas.",
        collection="transport_requests",
        columns=[
            ("origem", "Origem", 140),
            ("destino", "Destino", 140),
            ("data", "Data", 90),
            ("hora", "Hora", 70),
            ("empresa", "Empresa", 130),
            ("nome", "Nome", 120),
            ("telefone", "Telefone", 110),
            ("status", "Status", 110),
        ],
        normalizer=normalize_transport_request,
        id_prefix="treq",
        event_received="site.transport_request.received",
        form_builder=_transport_request_form,
        statuses=TRANSPORT_REQUEST_STATUSES,
    )


def _render_inbound_page(parent, app, page_key, title, subtitle, collection, columns, normalizer, id_prefix, event_received, form_builder, statuses):
    ensure_platform_collections(app)
    records = getattr(app, collection)

    parent.configure(bg=COLORS["bg"])
    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text=title, bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(title_box, text=subtitle, bg=COLORS["bg"], fg=COLORS["muted"], font=FONTS["small"], wraplength=760, justify="left").pack(anchor="w", pady=(2, 0))
    styled_button(header, "+ Novo registro", style="success", command=lambda: _open_form(app, page_key, collection, normalizer, id_prefix, event_received, form_builder, statuses)).pack(side="right", anchor="n")

    cards = tk.Frame(parent, bg=COLORS["bg"])
    cards.pack(fill="x", pady=(0, 12))
    _metric_card(cards, "Total", str(len(records)), "registros").pack(side="left", fill="x", expand=True, padx=(0, 8))
    _metric_card(cards, "Novos / Recebidas", str(_count_open(records, statuses)), "aguardando triagem").pack(side="left", fill="x", expand=True, padx=(0, 8))
    _metric_card(cards, "Origem Site", str(sum(1 for item in records if _origin_value(item) == ORIGIN_SITE)), "preparado para webhook").pack(side="left", fill="x", expand=True)

    box = panel_frame(parent)
    box.pack(fill="both", expand=True)
    tree_cols = [col[0] for col in columns]
    tree = ttk.Treeview(box, columns=tree_cols, show="headings", style="Custom.Treeview", height=14)
    for key, label, width in columns:
        tree.heading(key, text=label)
        tree.column(key, width=width, anchor="w")
    for item in records:
        tree.insert("", "end", iid=item.get("id"), values=tuple(item.get(key, "") for key in tree_cols))
    y_scroll = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=y_scroll.set)
    tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    y_scroll.pack(side="right", fill="y", pady=10)

    actions = tk.Frame(parent, bg=COLORS["bg"])
    actions.pack(fill="x", pady=8)
    styled_button(actions, "Detalhes", style="outline_primary", size="sm", command=lambda: _show_details(app, tree, collection)).pack(side="left", padx=(0, 6))
    styled_button(actions, "Editar", style="outline_primary", size="sm", command=lambda: _open_form(app, page_key, collection, normalizer, id_prefix, event_received, form_builder, statuses, _selected(app, tree, collection))).pack(side="left", padx=(0, 6))
    styled_button(actions, "Excluir", style="outline_danger", size="sm", command=lambda: _delete_record(app, parent, page_key, collection, tree, normalizer)).pack(side="left")


def _origin_value(item):
    return item.get("origem") or item.get("origem_fonte") or ORIGIN_SITE


def _count_open(records, statuses):
    open_statuses = {statuses[0]}
    if len(statuses) > 1:
        open_statuses.add(statuses[1])
    return sum(1 for item in records if item.get("status") in open_statuses)


def _metric_card(parent, title, value, hint):
    card = panel_frame(parent)
    tk.Label(card, text=title, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(10, 0))
    tk.Label(card, text=value, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=12)
    tk.Label(card, text=hint, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(0, 10))
    return card


def _selected(app, tree, collection):
    selection = tree.selection()
    if not selection:
        return None
    records = getattr(app, collection)
    return next((item for item in records if item.get("id") == selection[0]), None)


def _show_details(app, tree, collection):
    item = _selected(app, tree, collection)
    if not item:
        messagebox.showwarning("Detalhes", "Selecione um registro.", parent=app)
        return
    lines = [f"{key}: {value}" for key, value in item.items() if key != "payload"]
    messagebox.showinfo("Detalhes", "\n".join(lines), parent=app)


def _delete_record(app, parent, page_key, collection, tree, normalizer):
    item = _selected(app, tree, collection)
    if not item:
        messagebox.showwarning("Excluir", "Selecione um registro.", parent=app)
        return
    if not messagebox.askyesno("Excluir", "Confirma a exclusao do registro selecionado?", parent=app):
        return
    records = [row for row in getattr(app, collection) if row.get("id") != item.get("id")]
    setattr(app, collection, records)
    app.save_state()
    app.show_page(page_key)


def _open_form(app, page_key, collection, normalizer, id_prefix, event_received, form_builder, statuses, record=None):
    window = tk.Toplevel(app)
    editing = record is not None
    window.title("Editar registro" if editing else "Novo registro")
    window.configure(bg=COLORS["bg"])
    window.geometry("680x620")
    window.transient(app)
    window.grab_set()
    form, _canvas = scrollable_form(window)
    fields = {}
    form_builder(form, fields, record, statuses)
    footer = tk.Frame(window, bg=COLORS["bg"])
    footer.pack(fill="x", padx=12, pady=12)
    styled_button(footer, "Cancelar", style="secondary", command=window.destroy).pack(side="right", padx=(8, 0))
    styled_button(
        footer,
        "Salvar",
        style="success",
        command=lambda: _save_record(app, window, page_key, collection, normalizer, id_prefix, event_received, fields, record),
    ).pack(side="right")


def _save_record(app, window, page_key, collection, normalizer, id_prefix, event_received, fields, record):
    values = {key: resolve_widget_value(widget) if not isinstance(widget, ttk.Combobox) else widget.get() for key, widget in fields.items()}
    if isinstance(fields.get("observacoes"), tk.Text):
        values["observacoes"] = fields["observacoes"].get("1.0", "end-1c").strip()
    records = getattr(app, collection)
    payload = normalizer(
        {
            **(record or {}),
            **values,
            "id": (record or {}).get("id") or next_record_id(id_prefix, records),
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
    )
    if not _validate_required(payload, collection):
        messagebox.showwarning("Validacao", "Preencha os campos obrigatorios.", parent=window)
        return
    updated = False
    for index, row in enumerate(records):
        if row.get("id") == payload.get("id"):
            old_status = row.get("status")
            records[index] = payload
            updated = True
            if old_status != payload.get("status"):
                log_event(app, "inbound.status.changed", f'Status alterado para {payload.get("status")}', referencia_id=payload.get("id", ""))
            break
    if not updated:
        records.append(payload)
        log_event(app, event_received if payload.get("origem") == ORIGIN_SITE or payload.get("origem_fonte") == ORIGIN_SITE else "inbound.manual.created", f'Registro criado: {payload.get("id", "")}', referencia_id=payload.get("id", ""), origem=payload.get("origem") or payload.get("origem_fonte") or "painel")
    setattr(app, collection, records)
    app.save_state()
    window.destroy()
    app.show_page(page_key)


def _validate_required(payload, collection):
    if collection == "company_leads":
        return bool(payload.get("empresa") and payload.get("responsavel"))
    if collection == "driver_leads":
        return bool(payload.get("nome") and payload.get("telefone"))
    if collection == "transport_requests":
        return bool(payload.get("origem") and payload.get("destino") and payload.get("nome"))
    return True


def _company_lead_form(form, fields, record, statuses):
    settings_section(form, "Lead de empresa", "Dados recebidos do site ou cadastrados manualmente no painel master.")
    panel = tk.Frame(form, bg=COLORS["panel"])
    panel.pack(fill="x")
    data = record or {}
    for key, label, ph, required in [
        ("empresa", "Empresa", "Razao social ou nome", True),
        ("responsavel", "Responsavel", "Nome do responsavel", True),
        ("telefone", "Telefone", "Telefone", False),
        ("email", "Email", "email@empresa.com", False),
        ("cidade", "Cidade", "Cidade", False),
        ("estado", "Estado (UF)", "UF", False),
    ]:
        settings_field(panel, fields, key, label, data.get(key, ""), ph, required)
    _status_combo(panel, fields, statuses, data.get("status", statuses[0]))
    _origin_field(panel, fields, data.get("origem", ORIGIN_SITE))
    settings_field(panel, fields, "observacoes", "Observacoes", data.get("observacoes", ""), "Anotacoes internas")


def _driver_lead_form(form, fields, record, statuses):
    settings_section(form, "Lead de motorista", "Candidatos recebidos do site ou registrados manualmente.")
    panel = tk.Frame(form, bg=COLORS["panel"])
    panel.pack(fill="x")
    data = record or {}
    for key, label, ph, required in [
        ("nome", "Nome", "Nome completo", True),
        ("telefone", "Telefone", "Telefone", True),
        ("whatsapp", "WhatsApp", "WhatsApp", False),
        ("email", "Email", "email@exemplo.com", False),
        ("cidade", "Cidade", "Cidade", False),
        ("estado", "Estado (UF)", "UF", False),
        ("categoria", "Categoria CNH", "Ex: B, D, E", False),
    ]:
        settings_field(panel, fields, key, label, data.get(key, ""), ph, required)
    _status_combo(panel, fields, statuses, data.get("status", statuses[0]))
    _origin_field(panel, fields, data.get("origem", ORIGIN_SITE))
    settings_field(panel, fields, "observacoes", "Observacoes", data.get("observacoes", ""), "Anotacoes internas")


def _transport_request_form(form, fields, record, statuses):
    settings_section(form, "Solicitacao de transporte", "Pedido recebido do site ou registrado manualmente.")
    panel = tk.Frame(form, bg=COLORS["panel"])
    panel.pack(fill="x")
    data = record or {}
    for key, label, ph, required in [
        ("origem", "Origem", "Endereco ou local de partida", True),
        ("destino", "Destino", "Endereco ou local de chegada", True),
        ("data", "Data", "DD/MM/AAAA", False),
        ("hora", "Hora", "HH:MM", False),
        ("empresa", "Empresa", "Empresa solicitante", False),
        ("nome", "Nome", "Nome do solicitante", True),
        ("telefone", "Telefone", "Telefone", False),
        ("email", "Email", "email@exemplo.com", False),
    ]:
        settings_field(panel, fields, key, label, data.get(key, ""), ph, required)
    _status_combo(panel, fields, statuses, data.get("status", statuses[0]))
    _origin_field(panel, fields, data.get("origem_fonte", ORIGIN_SITE), key="origem_fonte")
    settings_field(panel, fields, "observacoes", "Observacoes", data.get("observacoes", ""), "Anotacoes internas")


def _status_combo(parent, fields, statuses, current):
    box = tk.Frame(parent, bg=COLORS["panel"])
    box.pack(fill="x", padx=14, pady=4)
    tk.Label(box, text="Status", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
    widget = ttk.Combobox(box, values=statuses, state="readonly", font=("Segoe UI", 10))
    widget.set(current or statuses[0])
    widget.pack(fill="x", pady=(3, 0))
    fields["status"] = widget


def _origin_field(parent, fields, value, key="origem"):
    box = tk.Frame(parent, bg=COLORS["panel"])
    box.pack(fill="x", padx=14, pady=4)
    tk.Label(box, text="Origem do registro", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
    entry = tk.Entry(box, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 10))
    entry.pack(fill="x", ipady=6, pady=(3, 0))
    entry.insert(0, value or ORIGIN_SITE)
    setup_placeholder(entry, ORIGIN_SITE)
    fields[key] = entry
