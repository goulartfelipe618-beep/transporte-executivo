"""Menu REDE — cadastro oficial da Rede Comercial (fonte para o Motor)."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import qrcode

from .components import resolve_widget_value
from .full_features import scrollable_form, settings_field, settings_section
from .partner_network import (
    booking_url,
    ensure_partner_networks,
    normalize_partner_network,
    sync_partner_state,
    toggle_rede_status,
)
from .partner_network_schema import TIPO_REDE_OPTIONS
from .rede_contributors_ui import open_contributors_window
from .table_ui import grid_table_cell, grid_table_header, render_action_buttons, table_scroll_host, truncate_text
from .theme import COLORS, FONTS, styled_button

QR_DIR = Path("data") / "rede_qrcodes"
REDE_STATUSES = ("Ativo", "Inativo")


def render_rede(parent, app):
    ensure_partner_networks(app)
    partners = app.partner_networks

    parent.configure(bg=COLORS["bg"])
    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))

    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Rede de Empresas Parceiras", bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(
        title_box,
        text="Fonte oficial do Motor. Campos editados aqui sao expostos em GET /api/v1/network/{slug}/{codigo}.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=820,
        justify="left",
    ).pack(anchor="w", pady=(2, 0))

    styled_button(header, "+ Nova empresa", style="success", command=lambda: _open_form(app)).pack(side="right", anchor="n")

    _, table = table_scroll_host(parent)
    weights = [1, 2, 1, 1, 1, 1, 2, 0]
    headers = ["ID", "Empresa", "Tipo", "Cidade", "Comissao", "Status", "Link", "Acoes"]
    grid_table_header(table, headers, weights, [70, 0, 80, 60, 70, 70, 0, 480])

    if not partners:
        empty = tk.Frame(table, bg=COLORS["panel"])
        empty.grid(row=1, column=0, columnspan=8, sticky="ew", padx=8, pady=24)
        tk.Label(empty, text="Nenhuma empresa cadastrada.", bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["small"]).pack()
    else:
        for row_index, partner in enumerate(partners, start=1):
            _add_row(table, app, partner, row_index)


def _add_row(table, app, partner, row_index):
    bg = COLORS["panel"] if row_index % 2 else COLORS["panel_alt"]
    link = booking_url(partner)
    status = partner.get("status", "Ativo")
    comissao = partner.get("comissao_rede", partner.get("comissao_pct", 0))
    values = [
        partner.get("id", ""),
        partner.get("nome_rede") or partner.get("nome", ""),
        partner.get("tipo_rede", "-"),
        partner.get("cidade", "-"),
        f"{comissao:g}%",
        status,
        truncate_text(link, 36) if link else "Pendente",
    ]
    for col, value in enumerate(values):
        fg = COLORS["success"] if col == 5 and status == "Ativo" else COLORS["danger"] if col == 5 else COLORS["text"]
        grid_table_cell(table, row_index, col, value, bg, fg=fg, truncate=28 if col == 1 else None)

    actions = tk.Frame(table, bg=bg)
    actions.grid(row=row_index, column=7, sticky="ew", padx=4, pady=5)
    toggle_label = "Desativar" if status == "Ativo" else "Ativar"
    render_action_buttons(
        actions,
        [
            ("Editar", lambda p=partner: _open_form(app, p), "primary"),
            ("Contrib.", lambda p=partner: open_contributors_window(app, p), "accent"),
            (toggle_label, lambda p=partner: _toggle_status(app, p), "warning" if status == "Ativo" else "success"),
            ("Copiar link", lambda p=partner: _copy_link(app, p), "secondary"),
            ("QR", lambda p=partner: _download_qr(app, p), "secondary"),
        ],
        bg=bg,
    )


def _combo_field(parent, fields, key, label, options, value=""):
    box = tk.Frame(parent, bg=COLORS["panel"])
    box.pack(fill="x", padx=14, pady=4)
    tk.Label(box, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9), anchor="w").pack(fill="x")
    var = tk.StringVar(value=value or (options[0] if options else ""))
    ttk.Combobox(box, textvariable=var, values=list(options), state="readonly", font=("Segoe UI", 10)).pack(fill="x", ipady=4, pady=(3, 0))
    fields[key] = var


def _open_form(app, partner=None):
    ensure_partner_networks(app)
    window = tk.Toplevel(app)
    window.title("Editar empresa" if partner else "Nova empresa da Rede")
    window.configure(bg=COLORS["bg"])
    window.geometry("680x820")
    window.minsize(580, 640)
    window.transient(app)
    window.grab_set()

    form, _ = scrollable_form(window)
    fields = {}
    data = dict(partner or {})

    settings_section(form, "Identidade da rede", "Nome, tipo e status publicados no Motor")
    panel = tk.Frame(form, bg=COLORS["panel"])
    panel.pack(fill="x")

    if partner and partner.get("id"):
        box = tk.Frame(panel, bg=COLORS["panel"])
        box.pack(fill="x", padx=14, pady=(8, 4))
        tk.Label(box, text="ID (fixo)", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
        tk.Label(box, text=partner["id"], bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w", pady=(2, 0))

    settings_field(panel, fields, "nome_rede", "Nome da rede", data.get("nome_rede") or data.get("nome", ""), "Ex.: Hotel Aurora", True)
    _combo_field(panel, fields, "tipo_rede", "Tipo da rede", TIPO_REDE_OPTIONS, data.get("tipo_rede", "AFILIADO"))
    _combo_field(panel, fields, "status", "Status", REDE_STATUSES, data.get("status", "Ativo"))

    settings_section(form, "Branding do Motor", "Cores e visual exibidos no Motor de Reservas")
    brand = tk.Frame(form, bg=COLORS["panel"])
    brand.pack(fill="x")
    for key, label, ph in [
        ("logo_url", "Logo (URL)", "https://.../logo.png"),
        ("banner_url", "Banner (URL)", "https://.../banner.jpg"),
        ("cor_primaria", "Cor primaria", "#0D1B2A"),
        ("cor_secundaria", "Cor secundaria", "#D4AF37"),
        ("texto_boas_vindas", "Texto de boas-vindas", "Mensagem no Motor"),
    ]:
        settings_field(brand, fields, key, label, data.get(key, ""), ph)

    settings_section(form, "Contato e localizacao", "Dados comerciais da parceira")
    contact = tk.Frame(form, bg=COLORS["panel"])
    contact.pack(fill="x")
    for key, label, ph, req in [
        ("telefone", "Telefone", "Telefone comercial", False),
        ("whatsapp", "WhatsApp", "WhatsApp comercial", False),
        ("email", "E-mail", "contato@empresa.com", False),
        ("cidade", "Cidade", "Cidade base", False),
        ("estado", "Estado (UF)", "UF", False),
        ("comissao_rede", "Comissao rede (%)", "Ex.: 10", True),
        ("observacoes", "Observacoes", "Informacoes internas", False),
    ]:
        settings_field(
            contact, fields, key, label,
            data.get(key, data.get("comissao_pct", "") if key == "comissao_rede" else ""),
            ph, req,
        )

    if partner and booking_url(partner):
        link_box = tk.Frame(contact, bg=COLORS["panel"])
        link_box.pack(fill="x", padx=14, pady=(8, 4))
        tk.Label(link_box, text="Link do motor", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
        tk.Label(link_box, text=booking_url(partner), bg=COLORS["panel"], fg=COLORS["accent"], font=FONTS["tiny"], wraplength=560, justify="left").pack(anchor="w", pady=(2, 0))

    footer = tk.Frame(window, bg=COLORS["bg"])
    footer.pack(fill="x", padx=12, pady=12)
    styled_button(footer, "Cancelar", style="secondary", command=window.destroy).pack(side="right", padx=(8, 0))
    styled_button(footer, "Salvar", style="success", command=lambda: _save(app, window, fields, partner)).pack(side="right")
    if partner:
        styled_button(footer, "Contribuidores", style="accent", command=lambda: open_contributors_window(app, partner)).pack(side="left")
        if booking_url(partner):
            styled_button(footer, "Copiar link", style="primary", command=lambda: _copy_link(app, partner, window)).pack(side="left", padx=(8, 0))
            styled_button(footer, "Baixar QR", style="secondary", command=lambda: _download_qr(app, partner, window)).pack(side="left", padx=(8, 0))


def _field_values(fields):
    values = {}
    for key, widget in fields.items():
        values[key] = widget.get().strip() if isinstance(widget, tk.StringVar) else resolve_widget_value(widget)
    return values


def _save(app, window, fields, partner):
    values = _field_values(fields)
    if not str(values.get("nome_rede", "")).strip():
        messagebox.showwarning("Validacao", "Informe o nome da rede.", parent=window)
        return
    if not str(values.get("comissao_rede", "")).strip():
        messagebox.showwarning("Validacao", "Informe a comissao da rede (%).", parent=window)
        return

    payload = normalize_partner_network({**(partner or {}), **values, "nome": values.get("nome_rede")}, app.partner_networks)
    updated = False
    for index, row in enumerate(app.partner_networks):
        if row.get("id") == payload.get("id"):
            app.partner_networks[index] = payload
            updated = True
            break
    if not updated:
        app.partner_networks.insert(0, payload)
    sync_partner_state(app)
    app.save_state()
    window.destroy()
    messagebox.showinfo("Empresa salva", f'"{payload.get("nome_rede")}" cadastrada.\n\nLink:\n{payload.get("booking_link")}', parent=app)
    app.show_page("REDE")


def _toggle_status(app, partner):
    updated = toggle_rede_status(partner)
    for index, row in enumerate(app.partner_networks):
        if row.get("id") == updated.get("id"):
            app.partner_networks[index] = {**row, **updated}
            break
    sync_partner_state(app)
    app.save_state()
    app.show_page("REDE")


def _copy_link(app, partner, parent=None):
    link = booking_url(partner)
    if not link:
        messagebox.showwarning("Link", "Salve a empresa para gerar o link.", parent=parent or app)
        return
    app.clipboard_clear()
    app.clipboard_append(link)
    messagebox.showinfo("Copiar link", f"Link copiado.\n\nStatus: {partner.get('status', 'Ativo')}", parent=parent or app)


def _qr_path(partner):
    QR_DIR.mkdir(parents=True, exist_ok=True)
    return QR_DIR / f"{partner.get('id', 'rede')}.png"


def _ensure_qr_file(partner):
    link = booking_url(partner)
    if not link:
        return None
    path = _qr_path(partner)
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(path)
    return path


def _download_qr(app, partner, parent=None):
    link = booking_url(partner)
    if not link:
        messagebox.showwarning("QR Code", "Salve a empresa para gerar o QR Code.", parent=parent or app)
        return
    source = _ensure_qr_file(partner)
    target = filedialog.asksaveasfilename(parent=parent or app, title="Salvar QR Code", defaultextension=".png", initialfile=f"qr-{partner.get('id', 'rede')}.png", filetypes=[("PNG", "*.png")])
    if not target:
        return
    Path(target).write_bytes(source.read_bytes())
    messagebox.showinfo("QR Code", f"QR Code salvo em:\n{target}", parent=parent or app)
