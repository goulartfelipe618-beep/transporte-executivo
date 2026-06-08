"""Configuracoes completas, clientes PF/PJ e helpers de UI reutilizaveis."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .company_model import (
    COMPANY_STATUSES,
    COMPANY_USER_PROFILES,
    COMPANY_USER_STATUSES,
    ensure_company_portal_structure,
    is_corporate_client,
    normalize_company_user,
)
from .portal_auth import is_password_hash, prepare_password_field
from .company_portal import company_portal_url
from .components import apply_input_rules, resolve_widget_value, setup_placeholder
from .settings_store import load_settings, save_settings
from .branding import apply_branding, resolve_font_family
from .table_ui import render_action_buttons
from .theme import COLORS, FONTS, badge_label, panel_frame, styled_button


def scrollable_form(parent, bg=None):
    bg = bg or COLORS["bg"]
    wrapper = tk.Frame(parent, bg=bg)
    wrapper.pack(fill="both", expand=True)
    canvas = tk.Canvas(wrapper, bg=bg, highlightthickness=0)
    scrollbar = tk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def on_configure(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(window_id, width=canvas.winfo_width())

    inner.bind("<Configure>", on_configure)
    canvas.bind("<Configure>", on_configure)

    def on_mousewheel(event):
        if not canvas.winfo_exists():
            return
        try:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            return

    canvas.bind_all("<MouseWheel>", on_mousewheel)
    wrapper.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"), add="+")
    return inner, canvas


def settings_field(parent, fields, key, label, value="", placeholder="", required=False):
    box = tk.Frame(parent, bg=COLORS["panel"])
    box.pack(fill="x", padx=14, pady=4)
    text = f"{label}{' *' if required else ''}"
    tk.Label(box, text=text, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9), anchor="w").pack(fill="x")
    entry = tk.Entry(box, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 10))
    entry.pack(fill="x", ipady=6, pady=(3, 0))
    apply_input_rules(entry, field_key=key, placeholder=placeholder, label=label, value=value)
    fields[key] = entry


def settings_section(parent, title, subtitle=None):
    head = tk.Frame(parent, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground="#D3DAE3")
    head.pack(fill="x", padx=12, pady=(14, 6))
    tk.Label(head, text=title, bg=COLORS["panel_alt"], fg=COLORS["primary"], font=("Segoe UI Semibold", 11)).pack(anchor="w", padx=12, pady=(10, 0))
    if subtitle:
        tk.Label(head, text=subtitle, bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 8), wraplength=900, justify="left").pack(anchor="w", padx=12, pady=(2, 10))


def _settings_card(parent, title, subtitle, accent):
    card = panel_frame(parent, bg=COLORS["panel"])
    card.pack(fill="x", pady=(0, 14))
    tk.Frame(card, bg=accent, height=3).pack(fill="x")
    head = tk.Frame(card, bg=COLORS["panel"])
    head.pack(fill="x", padx=18, pady=(14, 0))
    tk.Label(head, text=title, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 12)).pack(anchor="w")
    tk.Label(head, text=subtitle, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"], wraplength=820, justify="left").pack(anchor="w", pady=(2, 0))
    body = tk.Frame(card, bg=COLORS["panel"])
    body.pack(fill="x", padx=18, pady=(10, 16))
    return body


def _settings_grid_field(parent, fields, editables, spec, data, row, col, colspan=1):
    key, label, placeholder, required = spec
    box = tk.Frame(parent, bg=COLORS["panel"])
    box.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=6)
    text = f"{label}{' *' if required else ''}"
    tk.Label(box, text=text, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w")
    entry = tk.Entry(box, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 10))
    entry.pack(fill="x", ipady=7, pady=(4, 0))
    apply_input_rules(entry, field_key=key, placeholder=placeholder, label=label, value=data.get(key, ""))
    fields[key] = entry
    editables.append(("entry", entry))


def _fill_settings_grid(parent, fields, editables, specs, data):
    row = 0
    col = 0
    for spec in specs:
        span = 2 if spec[0] in {"endereco_completo", "endereco_sede"} else 1
        _settings_grid_field(parent, fields, editables, spec, data, row=row, col=col, colspan=span)
        if span == 2:
            row += 1
            col = 0
        else:
            col += 1
            if col > 1:
                col = 0
                row += 1


def _lock_entry(entry, locked=True):
    if locked:
        entry.configure(state="disabled", disabledbackground=COLORS["panel_alt"], disabledforeground=COLORS["text"])
    else:
        entry.configure(state="normal", bg=COLORS["input"], fg=COLORS["text"])


def _settings_field_value(widget):
    if widget is None:
        return ""
    if isinstance(widget, tk.StringVar):
        return widget.get().strip()
    return resolve_widget_value(widget)


def render_settings(parent, app):
    parent.configure(bg=COLORS["bg"])
    data = load_settings()
    fields = {}
    editables = []
    editing = {"active": False}
    snapshot = {}

    header = panel_frame(parent)
    header.pack(fill="x", pady=(0, 12))
    tk.Frame(header, bg=COLORS["primary"], height=3).pack(fill="x")
    header_inner = tk.Frame(header, bg=COLORS["panel"])
    header_inner.pack(fill="x", padx=18, pady=16)

    title_row = tk.Frame(header_inner, bg=COLORS["panel"])
    title_row.pack(fill="x")
    title_box = tk.Frame(title_row, bg=COLORS["panel"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Configuracoes do Sistema", bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(
        title_box,
        text="Parametros da operacao, identidade visual e dados contratuais.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=FONTS["small"],
    ).pack(anchor="w", pady=(2, 0))

    actions = tk.Frame(title_row, bg=COLORS["panel"])
    actions.pack(side="right", anchor="n")
    mode_badge = badge_label(actions, "Somente leitura", tone="neutral")
    mode_badge.pack(side="left", padx=(0, 10))

    edit_btn = styled_button(actions, "Editar", style="primary", command=lambda: _start_settings_edit())
    edit_btn.pack(side="left", padx=(0, 6))
    cancel_btn = styled_button(actions, "Cancelar", style="secondary", command=lambda: _cancel_settings_edit())
    save_btn = styled_button(actions, "Salvar alteracoes", style="success", command=lambda: _save_settings_form(app, fields, _finish_save))
    cancel_btn.pack_forget()
    save_btn.pack_forget()

    pills = tk.Frame(header_inner, bg=COLORS["panel"])
    pills.pack(fill="x", pady=(14, 0))
    for label, value, tone in [
        ("Projeto", data.get("nome_projeto", "-"), "primary"),
        ("Empresa", data.get("empresa", "-"), "neutral"),
        ("Contato", data.get("email", "-"), "neutral"),
    ]:
        pill = tk.Frame(pills, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
        pill.pack(side="left", padx=(0, 8))
        tk.Label(pill, text=label.upper(), bg=COLORS["panel_alt"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(8, 0))
        fg = COLORS["primary"] if tone == "primary" else COLORS["text"]
        tk.Label(pill, text=str(value)[:42], bg=COLORS["panel_alt"], fg=fg, font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=12, pady=(0, 8))

    host = tk.Frame(parent, bg=COLORS["bg"])
    host.pack(fill="both", expand=True)
    canvas = tk.Canvas(host, bg=COLORS["bg"], highlightthickness=0)
    scrollbar = tk.Scrollbar(host, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    body = tk.Frame(canvas, bg=COLORS["bg"])
    window_id = canvas.create_window((0, 0), window=body, anchor="nw")

    def _sync_scroll(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _sync_width(event):
        canvas.itemconfigure(window_id, width=event.width)

    def _wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    body.bind("<Configure>", _sync_scroll)
    canvas.bind("<Configure>", _sync_width)
    canvas.bind("<MouseWheel>", _wheel)
    body.bind("<MouseWheel>", _wheel)

    profile_body = _settings_card(body, "Meu Perfil", "Dados pessoais e da empresa operadora", COLORS["primary"])
    profile_grid = tk.Frame(profile_body, bg=COLORS["panel"])
    profile_grid.pack(fill="x")
    profile_grid.grid_columnconfigure(0, weight=1)
    profile_grid.grid_columnconfigure(1, weight=1)
    profile_fields = [
        ("nome_completo", "Nome completo", "Nome completo", True),
        ("email", "E-mail", "email@empresa.com", True),
        ("telefone", "Telefone", "Telefone", True),
        ("empresa", "Nome da empresa", "Nome da empresa", True),
        ("cnpj_opcional", "CNPJ (opcional)", "CNPJ", False),
        ("cidade", "Cidade", "Cidade", True),
        ("uf", "Estado (UF)", "UF", True),
        ("endereco_completo", "Endereco completo", "Endereco completo", True),
    ]
    _fill_settings_grid(profile_grid, fields, editables, profile_fields, data)

    brand_body = _settings_card(body, "Identidade visual", "Logomarca, nome do projeto e tipografia global", COLORS["accent"])
    logo_row = tk.Frame(brand_body, bg=COLORS["panel"])
    logo_row.pack(fill="x", pady=(0, 10))
    tk.Label(logo_row, text="Logomarca global", bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w")
    logo_line = tk.Frame(logo_row, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
    logo_line.pack(fill="x", pady=(4, 0))
    logo_var = tk.StringVar(value=data.get("logo_global", "") or "Nenhuma imagem selecionada")
    fields["logo_global"] = logo_var
    tk.Label(logo_line, textvariable=logo_var, bg=COLORS["panel_alt"], fg=COLORS["text"], font=FONTS["small"], anchor="w", padx=12, pady=10).pack(side="left", fill="x", expand=True)
    logo_btn = styled_button(logo_line, "Escolher imagem", style="outline_primary", size="sm", command=lambda: _pick_file(logo_var))
    logo_btn.pack(side="right", padx=8, pady=6)
    editables.append(("button", logo_btn))

    brand_grid = tk.Frame(brand_body, bg=COLORS["panel"])
    brand_grid.pack(fill="x")
    brand_grid.grid_columnconfigure(0, weight=1)
    brand_grid.grid_columnconfigure(1, weight=1)
    _settings_grid_field(brand_grid, fields, editables, ("nome_projeto", "Nome global do sistema", "DRIVE PREMIUM", True), data, row=0, col=0)
    _settings_grid_field(brand_grid, fields, editables, ("fonte_global", "Fonte global", "Poppins", True), data, row=0, col=1)
    preview_box = tk.Frame(brand_body, bg=COLORS["primary_soft"], highlightthickness=1, highlightbackground=COLORS["primary"])
    preview_box.pack(fill="x", pady=(10, 0))
    preview = tk.Label(
        preview_box,
        text=f'Preview: {data.get("nome_projeto", "DRIVE PREMIUM")} — fonte {data.get("fonte_global", "Poppins")}',
        bg=COLORS["primary_soft"],
        fg=COLORS["primary_dark"],
        font=(data.get("fonte_global", "Segoe UI"), 11),
        anchor="w",
        padx=14,
        pady=12,
    )
    preview.pack(fill="x")

    def _refresh_preview(_event=None):
        preview.configure(
            text=f'Preview: {_settings_field_value(fields.get("nome_projeto")) or "Projeto"} — fonte {_settings_field_value(fields.get("fonte_global")) or "Segoe UI"}',
            font=(_settings_field_value(fields.get("fonte_global")) or "Segoe UI", 11),
        )

    contract_body = _settings_card(body, "Informacoes contratuais", "Cabecalho legal dos contratos e documentos", COLORS["success"])
    cnpj_var = tk.StringVar(value=data.get("possui_cnpj", "sim"))
    fields["possui_cnpj"] = cnpj_var
    radio = tk.Frame(contract_body, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
    radio.pack(fill="x", pady=(0, 10))
    tk.Label(radio, text="Possui CNPJ da empresa?", bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(side="left", padx=12, pady=10)
    rb_sim = tk.Radiobutton(radio, text="Sim", variable=cnpj_var, value="sim", bg=COLORS["panel_alt"], fg=COLORS["text"], selectcolor=COLORS["panel_alt"], activebackground=COLORS["panel_alt"])
    rb_sim.pack(side="left", padx=(0, 8))
    rb_nao = tk.Radiobutton(radio, text="Nao", variable=cnpj_var, value="nao", bg=COLORS["panel_alt"], fg=COLORS["text"], selectcolor=COLORS["panel_alt"], activebackground=COLORS["panel_alt"])
    rb_nao.pack(side="left")
    editables.extend([("radio", rb_sim), ("radio", rb_nao)])

    contract_grid = tk.Frame(contract_body, bg=COLORS["panel"])
    contract_grid.pack(fill="x")
    contract_grid.grid_columnconfigure(0, weight=1)
    contract_grid.grid_columnconfigure(1, weight=1)
    contract_fields = [
        ("razao_social", "Razao social", "Razao social", True),
        ("cnpj_contrato", "CNPJ", "CNPJ", True),
        ("endereco_sede", "Endereco da sede", "Endereco", True),
        ("representante_legal", "Representante legal", "Nome", True),
        ("telefone_contrato", "Telefone", "Telefone", True),
        ("whatsapp_contrato", "WhatsApp", "WhatsApp", True),
        ("email_oficial", "E-mail oficial", "E-mail", True),
    ]
    _fill_settings_grid(contract_grid, fields, editables, contract_fields, data)

    sign_body = _settings_card(body, "Assinatura eletronica", "Imagem usada em PDFs e documentos oficiais", COLORS["warning"])
    sig_row = tk.Frame(sign_body, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
    sig_row.pack(fill="x")
    sig_var = tk.StringVar(value=data.get("assinatura", "") or "Nenhuma assinatura configurada")
    fields["assinatura"] = sig_var
    tk.Label(sig_row, textvariable=sig_var, bg=COLORS["panel_alt"], fg=COLORS["text"], font=FONTS["small"], anchor="w", padx=12, pady=10).pack(side="left", fill="x", expand=True)
    sig_btn = styled_button(sig_row, "Enviar assinatura", style="outline_primary", size="sm", command=lambda: _pick_file(sig_var))
    sig_btn.pack(side="right", padx=8, pady=6)
    editables.append(("button", sig_btn))

    sec_body = _settings_card(body, "Seguranca", "Credenciais de acesso e autenticacao em dois fatores", COLORS["danger"])
    sec_actions = tk.Frame(sec_body, bg=COLORS["panel"])
    sec_actions.pack(fill="x")
    styled_button(sec_actions, "Alterar senha de acesso", style="primary", command=lambda: messagebox.showinfo("Seguranca", "Alteracao de senha em breve.", parent=app)).pack(side="left", padx=(0, 8))
    styled_button(sec_actions, "Configurar 2FA (TOTP)", style="secondary", command=lambda: messagebox.showinfo("2FA", "Autenticacao em 2 fatores em breve.", parent=app)).pack(side="left")

    hint = tk.Label(
        body,
        text="Clique em Editar para alterar os dados. Fora do modo edicao, as informacoes ficam protegidas contra alteracoes acidentais.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["tiny"],
        wraplength=900,
        justify="left",
    )
    hint.pack(anchor="w", pady=(0, 8))

    def _field_snapshot():
        snap = {}
        for key, widget in fields.items():
            if isinstance(widget, tk.StringVar):
                snap[key] = widget.get()
            else:
                snap[key] = resolve_widget_value(widget)
        return snap

    def _apply_snapshot(snap):
        for key, widget in fields.items():
            value = snap.get(key, "")
            if isinstance(widget, tk.StringVar):
                widget.set(value)
            elif isinstance(widget, tk.Entry):
                widget.configure(state="normal")
                widget.delete(0, "end")
                if value:
                    widget.insert(0, value)
            _refresh_preview()

    def _set_editing(active):
        editing["active"] = active
        for item in editables:
            kind, widget = item
            if kind == "entry":
                _lock_entry(widget, locked=not active)
            elif kind == "button":
                widget.configure(state="normal" if active else "disabled")
            elif kind == "radio":
                widget.configure(state="normal" if active else "disabled")
        if active:
            mode_badge.configure(text="Editando", bg=COLORS["warning_soft"], fg=COLORS["warning"])
            edit_btn.pack_forget()
            cancel_btn.pack(side="left", padx=(0, 6))
            save_btn.pack(side="left")
            for key in ("nome_projeto", "fonte_global"):
                widget = fields.get(key)
                if isinstance(widget, tk.Entry):
                    widget.bind("<KeyRelease>", _refresh_preview)
        else:
            mode_badge.configure(text="Somente leitura", bg=COLORS["chip"], fg=COLORS["text"])
            cancel_btn.pack_forget()
            save_btn.pack_forget()
            edit_btn.pack(side="left", padx=(0, 6))

    def _exit_edit_mode():
        _set_editing(False)

    def _finish_save():
        snapshot.clear()
        snapshot.update(_field_snapshot())
        _exit_edit_mode()

    def _start_settings_edit():
        snapshot.clear()
        snapshot.update(_field_snapshot())
        _set_editing(True)

    def _cancel_settings_edit():
        _apply_snapshot(snapshot)
        _set_editing(False)

    _set_editing(False)
    parent.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"), add="+")


def _pick_file(var):
    path = filedialog.askopenfilename(filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")])
    if path:
        var.set(path)


def _save_settings_form(app, fields, on_done=None):
    payload = {}
    for key, widget in fields.items():
        if isinstance(widget, tk.StringVar):
            payload[key] = widget.get().strip()
        else:
            payload[key] = resolve_widget_value(widget)
    requested_font = payload.get("fonte_global", "")
    resolved_font = resolve_font_family(requested_font)
    save_settings(payload)
    apply_branding(payload)
    if requested_font and resolved_font == "Segoe UI" and requested_font.lower() not in {"segoe ui", "segoe"}:
        messagebox.showwarning(
            "Fonte nao encontrada",
            f'A fonte "{requested_font}" nao esta instalada no sistema. Usando Segoe UI.\n\n'
            "Instale a fonte no Windows e reinicie o app para aplicar.",
            parent=app,
        )
    if hasattr(app, "refresh_branding"):
        app.refresh_branding()
    else:
        messagebox.showinfo(
            "Configuracoes",
            "Configuracoes salvas. Reinicie o sistema para aplicar nome e fonte em todo o painel.",
            parent=app,
        )
        if on_done:
            on_done()
        return
    messagebox.showinfo("Configuracoes", "Configuracoes salvas e identidade visual aplicada.", parent=app)
    if on_done:
        on_done()


# --- CLIENTES ---

def render_clients(parent, app):
    parent.configure(bg=COLORS["bg"])
    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 10))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Empresas Corporativas", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI Semibold", 18)).pack(anchor="w")
    tk.Label(title_box, text="Cadastro de empresas clientes — gera link em business.transporteexecutivo.com.", bg=COLORS["bg"], fg=COLORS["muted"], font=FONTS["small"]).pack(anchor="w", pady=(2, 0))
    styled_button(header, "+ Cadastrar empresa", style="success", command=lambda: open_client_type_modal(app)).pack(side="right")

    search = tk.Entry(parent, bg=COLORS["panel"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
    search.pack(fill="x", ipady=7, pady=(0, 10))
    setup_placeholder(search, "Buscar por nome, CPF/CNPJ, telefone ou e-mail...")

    render_client_table(parent, app)


def render_client_table(parent, app):
    box = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    box.pack(fill="both", expand=True)
    if not app.clients:
        tk.Label(box, text="Nenhum cliente cadastrado ainda.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(pady=40)
        return

    cols = ("nome", "tipo", "documento", "telefone", "email")
    tree = ttk.Treeview(box, columns=cols, show="headings", style="Custom.Treeview", height=12)
    for col in cols:
        tree.heading(col, text=col.upper())
        tree.column(col, width=120, minwidth=70, anchor="w", stretch=True)
    for client in app.clients:
        tree.insert("", "end", iid=client.get("id", client.get("nome")), values=(
            client_display_name(client),
            "PJ" if client.get("tipo_pessoa") == "juridica" else "PF",
            client_document(client),
            client.get("telefone", ""),
            client.get("email", ""),
        ))
    y_scroll = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=y_scroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    box.grid_rowconfigure(0, weight=1)
    box.grid_columnconfigure(0, weight=1)

    actions = tk.Frame(parent, bg=COLORS["bg"])
    actions.pack(fill="x", pady=8)
    render_action_buttons(
        actions,
        [
            ("Detalhes", lambda: _client_action(app, tree, show_client_details)),
            ("Editar", lambda: _client_action(app, tree, lambda a, c: open_client_form(a, c))),
            ("Portal", lambda: _client_action(app, tree, copy_company_portal_link)),
            ("Excluir", lambda: _client_action(app, tree, delete_client)),
        ],
        bg=COLORS["bg"],
    )


def client_display_name(client):
    return client.get("nome") or client.get("nome_fantasia") or client.get("razao_social", "")


def client_document(client):
    return client.get("documento") or client.get("cpf") or client.get("cnpj", "")


def _client_action(app, tree, callback):
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Clientes", "Selecione um cliente na lista.", parent=app)
        return
    client = next((c for c in app.clients if str(c.get("id", c.get("nome"))) == sel[0] or client_display_name(c) == tree.item(sel[0])["values"][0]), None)
    if not client:
        idx = tree.index(sel[0])
        if idx < len(app.clients):
            client = app.clients[idx]
    if client:
        callback(app, client)


def copy_company_portal_link(app, client):
    if not is_corporate_client(client):
        messagebox.showwarning("Portal", "Portal disponivel apenas para empresas PJ.", parent=app)
        return
    base = company_portal_url(app)
    client.update(ensure_company_portal_structure(client, None, app.clients))
    app.save_state()
    link = client.get("portal_link", "")
    if not link:
        messagebox.showwarning("Portal", "Portal ainda nao configurado.", parent=app)
        return
    app.clipboard_clear()
    app.clipboard_append(link)
    messagebox.showinfo("Portal da Empresa", f"Link copiado:\n{link}", parent=app)


def open_client_type_modal(app):
    win = tk.Toplevel(app)
    win.title("Tipo de cadastro")
    win.configure(bg=COLORS["bg"])
    win.geometry("380x220")
    win.transient(app)
    win.grab_set()
    tk.Label(win, text="Qual tipo deseja cadastrar?", bg=COLORS["bg"], font=("Segoe UI Semibold", 12)).pack(pady=20)
    styled_button(win, "Pessoa fisica", style="primary", command=lambda: (win.destroy(), open_client_form(app, None, "fisica"))).pack(pady=6)
    styled_button(win, "Empresa corporativa (PJ)", style="secondary", command=lambda: (win.destroy(), open_client_form(app, None, "juridica"))).pack(pady=6)


def open_client_form(app, client=None, client_type=None):
    tipo = client_type or client.get("tipo_pessoa", "fisica")
    win = tk.Toplevel(app)
    win.title("Editar cliente" if client else "Cadastrar cliente")
    win.configure(bg=COLORS["bg"])
    win.geometry("760x760")
    win.minsize(640, 520)
    win.transient(app)
    win.grab_set()

    shell = tk.Frame(win, bg=COLORS["bg"])
    shell.pack(fill="both", expand=True, padx=10, pady=10)
    form, canvas = scrollable_form(shell)
    fields = {}
    tk.Label(form, text="Cadastrar cliente", bg=COLORS["panel"], fg=COLORS["primary"], font=("Segoe UI Semibold", 14)).pack(anchor="w", padx=14, pady=(12, 4))
    tk.Label(form, text="Dados visiveis apenas para a sua conta.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(0, 10))

    if tipo == "juridica":
        _build_company_form(form, fields, client)
    else:
        _build_person_form(form, fields, client)

    footer = tk.Frame(form, bg=COLORS["panel"])
    footer.pack(fill="x", padx=14, pady=16)
    styled_button(footer, "Cancelar", style="secondary", command=win.destroy).pack(side="right")
    styled_button(footer, "Cadastrar" if not client else "Salvar", style="success", command=lambda: save_client_form(app, win, fields, client, tipo)).pack(side="right", padx=(0, 8))
    form.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"))


def _build_person_form(parent, fields, client):
    c = client or {}
    client_input(parent, fields, "nome", "Nome completo *", c, "Nome e apelidos", True)
    client_input(parent, fields, "documento", "CPF / CNPJ (opcional)", c, "Opcional")
    client_input(parent, fields, "email", "E-mail", c, "email@cliente.com")
    client_input(parent, fields, "telefone", "Telefone 1", c, "Telefone")
    client_input(parent, fields, "telefone_2", "Telefone 2", c, "Telefone 2")
    addresses_block(parent, fields, c)


def _build_company_form(parent, fields, client):
    c = client or {}
    if c:
        c = ensure_company_portal_structure(dict(c), company_portal_url(parent.winfo_toplevel()), [])
    settings_section(parent, "Dados corporativos", "Empresa contratante vinculada ao Portal da Empresa")
    client_input(parent, fields, "razao_social", "Razao social *", c, "Razao social", True)
    client_input(parent, fields, "nome_fantasia", "Nome fantasia", c, "Nome fantasia")
    client_input(parent, fields, "cnpj", "CNPJ *", c, "00.000.000/0000-00", True)
    client_input(parent, fields, "inscricao_estadual", "Inscricao estadual", c, "IE")
    client_input(parent, fields, "email", "E-mail corporativo", c, "contato@empresa.com")
    client_input(parent, fields, "telefone", "Telefone principal", c, "Telefone")
    client_input(parent, fields, "telefone_2", "Telefone secundario", c, "Telefone")
    client_input(parent, fields, "responsavel", "Responsavel", c, "Nome do responsavel")
    addresses_block(parent, fields, c)

    status_box = tk.Frame(parent, bg=COLORS["panel"])
    status_box.pack(fill="x", padx=14, pady=4)
    tk.Label(status_box, text="Status da empresa", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
    status_combo = ttk.Combobox(status_box, values=COMPANY_STATUSES, state="readonly", font=("Segoe UI", 10))
    status_combo.set(c.get("status_empresa", "Ativa"))
    status_combo.pack(fill="x", pady=(3, 0))
    fields["status_empresa"] = status_combo

    portal_box = tk.Frame(parent, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground="#D3DAE3")
    portal_box.pack(fill="x", padx=14, pady=10)
    tk.Label(portal_box, text="Portal da Empresa (business.transporteexecutivo.com)", bg=COLORS["panel_alt"], font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=10, pady=8)
    tk.Label(portal_box, text=f"Link de login: {c.get('portal_link', 'Gerado automaticamente ao salvar')}", bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 9), wraplength=680, justify="left").pack(anchor="w", padx=10, pady=(0, 8))
    tk.Label(portal_box, text="Colaboradores com comissao propria sao cadastrados no menu REDE.", bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 8), wraplength=680, justify="left").pack(anchor="w", padx=10, pady=(0, 8))


def users_block(parent, fields, client):
    block = tk.Frame(parent, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground="#D3DAE3")
    block.pack(fill="x", padx=14, pady=10)
    tk.Label(block, text="Usuarios da empresa", bg=COLORS["panel_alt"], font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=10, pady=8)
    tk.Label(block, text="Usuarios corporativos com login exclusivo no Portal da Empresa.", bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=10)
    listbox = tk.Listbox(block, height=5, font=("Segoe UI", 9))
    listbox.pack(fill="x", padx=10, pady=8)
    fields["_users_listbox"] = listbox
    fields["_company_users"] = list(fields.get("_existing_users") or client.get("usuarios") or [])

    def refresh_users():
        listbox.delete(0, "end")
        for user in fields["_company_users"]:
            listbox.insert("end", f'{user.get("nome", "")} | {user.get("email", "")} | {user.get("perfil", "")} | {user.get("status", "")}')

    refresh_users()

    actions = tk.Frame(block, bg=COLORS["panel_alt"])
    actions.pack(fill="x", padx=10, pady=(0, 8))
    styled_button(actions, "+ Usuario", style="outline_primary", size="sm", command=lambda: open_company_user_form(parent.winfo_toplevel(), fields, refresh_users)).pack(side="left", padx=(0, 6))
    styled_button(actions, "Remover", style="outline_danger", size="sm", command=lambda: remove_selected_user(fields, listbox, refresh_users)).pack(side="left")


def remove_selected_user(fields, listbox, refresh):
    selection = listbox.curselection()
    if not selection:
        return
    fields["_company_users"].pop(selection[0])
    refresh()


def open_company_user_form(app, fields, refresh):
    win = tk.Toplevel(app)
    win.title("Usuario corporativo")
    win.configure(bg=COLORS["bg"])
    win.geometry("520x420")
    win.transient(app)
    win.grab_set()
    panel = tk.Frame(win, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    panel.pack(fill="both", expand=True, padx=12, pady=12)
    user_fields = {}
    for key, label, ph in [
        ("nome", "Nome *", "Nome completo"),
        ("email", "Email *", "email@empresa.com"),
        ("telefone", "Telefone", "Telefone"),
        ("senha", "Senha *", "Senha inicial"),
    ]:
        settings_field(panel, user_fields, key, label, "", ph, key != "telefone")
    perfil_box = tk.Frame(panel, bg=COLORS["panel"])
    perfil_box.pack(fill="x", padx=14, pady=4)
    tk.Label(perfil_box, text="Perfil", bg=COLORS["panel"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
    perfil = ttk.Combobox(perfil_box, values=COMPANY_USER_PROFILES, state="readonly")
    perfil.set("Solicitante")
    perfil.pack(fill="x", pady=(3, 0))
    status = ttk.Combobox(perfil_box, values=COMPANY_USER_STATUSES, state="readonly")
    status.set("Ativo")
    user_fields["perfil"] = perfil
    user_fields["status"] = status
    footer = tk.Frame(win, bg=COLORS["bg"])
    footer.pack(fill="x", padx=12, pady=12)
    styled_button(footer, "Cancelar", style="secondary", command=win.destroy).pack(side="right", padx=(8, 0))
    styled_button(footer, "Adicionar", style="success", command=lambda: add_company_user(win, user_fields, fields, refresh)).pack(side="right")


def add_company_user(window, user_fields, fields, refresh):
    values = {key: resolve_widget_value(widget) if not isinstance(widget, ttk.Combobox) else widget.get() for key, widget in user_fields.items()}
    if not values.get("nome") or not values.get("email") or not values.get("senha"):
        messagebox.showwarning("Usuario", "Informe nome, email e senha.", parent=window)
        return
    company_id = "emp-pending"
    fields["_company_users"].append(normalize_company_user(values, company_id))
    refresh()
    window.destroy()


def client_input(parent, fields, key, label, client, placeholder="", required=False):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=14, pady=(8, 2))
    entry = tk.Entry(parent, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 10))
    entry.pack(fill="x", padx=14, ipady=6)
    apply_input_rules(entry, field_key=key, placeholder=placeholder, label=label, value=client.get(key, ""))
    fields[key] = entry


def addresses_block(parent, fields, client):
    block = tk.Frame(parent, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground="#D3DAE3")
    block.pack(fill="x", padx=14, pady=10)
    tk.Label(block, text="Enderecos", bg=COLORS["panel_alt"], font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=10, pady=8)
    lines = tk.Frame(block, bg=COLORS["panel_alt"])
    lines.pack(fill="x", padx=10, pady=(0, 8))

    def add_line(tipo_val="", end_val=""):
        row = tk.Frame(lines, bg=COLORS["panel_alt"])
        row.pack(fill="x", pady=4)
        t = tk.Entry(row, font=("Segoe UI", 9))
        t.pack(side="left", fill="x", expand=True, padx=(0, 6))
        e = tk.Entry(row, font=("Segoe UI", 9))
        e.pack(side="left", fill="x", expand=True)
        if tipo_val:
            t.insert(0, tipo_val)
        else:
            setup_placeholder(t, "Tipo (casa, trabalho…)")
        if end_val:
            e.insert(0, end_val)
        else:
            setup_placeholder(e, "Rua, numero, cidade…")
        fields.setdefault("_addr_rows", []).append((t, e))

    add_line(client.get("endereco_tipo", "casa"), client.get("endereco", ""))
    styled_button(block, "+ Linha", style="outline_primary", size="sm", command=lambda: add_line()).pack(anchor="w", padx=10, pady=(0, 8))


def save_client_form(app, window, fields, client=None, client_type="fisica"):
    values = {k: resolve_widget_value(w) for k, w in fields.items() if not k.startswith("_")}
    nome = values.get("nome") or values.get("razao_social") or values.get("nome_fantasia")
    if not nome:
        messagebox.showwarning("Cliente", "Informe o nome do cliente.", parent=window)
        return
    enderecos = []
    for tipo_w, end_w in fields.get("_addr_rows", []):
        tipo = resolve_widget_value(tipo_w)
        end = resolve_widget_value(end_w)
        if end:
            enderecos.append({"tipo": tipo or "outro", "endereco": end})
    values["tipo_pessoa"] = client_type
    values["id"] = (client or {}).get("id", f"cli-{len(app.clients)+1}")
    if enderecos:
        values["endereco"] = enderecos[0]["endereco"]
        values["endereco_tipo"] = enderecos[0]["tipo"]
        values["enderecos"] = enderecos
    if client_type == "juridica":
        values["nome"] = values.get("nome_fantasia") or values.get("razao_social")
        values = ensure_company_portal_structure(values, None, app.clients)
    if client:
        client.update(values)
    else:
        app.clients.append(values)
    app.save_state()
    window.destroy()
    app.show_page("CLIENTES")
    if client_type == "juridica" and values.get("portal_link"):
        messagebox.showinfo(
            "Portal da Empresa",
            f"Portal criado/atualizado.\n\n{values.get('portal_link', '')}\n\nAcesso com e-mail corporativo e senha no portal business.",
            parent=app,
        )


def show_client_details(app, client):
    lines = [f"{k}: {v}" for k, v in client.items() if v and not k.startswith("_")]
    messagebox.showinfo("Detalhes do cliente", "\n".join(lines) or "Sem dados", parent=app)


def delete_client(app, client):
    if messagebox.askyesno("Excluir", f"Excluir {client_display_name(client)}?", parent=app):
        app.clients.remove(client)
        app.save_state()
        app.show_page("CLIENTES")
