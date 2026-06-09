import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .components import (
    apply_input_rules,
    parse_br_datetime,
    resolve_widget_value,
    set_input_value,
    setup_date_mask,
    setup_placeholder,
    validate_email_field,
    validate_future_datetime,
)
from .address_po_field import add_po_address_field, collect_address_values
from .domain.formatters import format_amount, parse_amount
from .portal_auth import active_portal_drivers, find_driver_by_name
from .reservation_numbers import next_reservation_number, next_reservation_numbers
from .reservation_pdf import default_pdf_filename, generate_reservation_pdf
from .table_ui import grid_table_cell, grid_table_header, render_action_buttons, table_scroll_host
from .theme import COLORS, styled_button


FIELDS = [
    ("cliente", "Cliente"),
    ("contato", "Contato"),
    ("email", "E-mail"),
    ("tipo", "Tipo"),
    ("trajeto", "Trajeto"),
    ("data", "Data"),
    ("motorista", "Motorista"),
    ("valor", "Valor"),
    ("status", "Status"),
]


def render_reservations_page(parent, app):
    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 10))

    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left")
    tk.Label(title_box, text="Reservas", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI Semibold", 18)).pack(anchor="w")
    tk.Label(title_box, text=f"Transfer ({len(app.reservations)})", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 11)).pack(anchor="w")

    buttons = tk.Frame(header, bg=COLORS["bg"])
    buttons.pack(side="right")
    styled_button(buttons, "Atualizar", style="secondary", command=lambda: app.show_page("RESERVAS")).pack(side="left", padx=(0, 8))
    styled_button(buttons, "+ Criar Reserva", style="success", size="lg", command=lambda: open_create_reservation_form(app)).pack(side="left")

    render_filters(parent)
    render_reservation_table(parent, app)


def render_filters(parent):
    box = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground="#D3DAE3")
    box.pack(fill="x", pady=(0, 10))

    tk.Label(box, text="Filtros", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6), columnspan=5)

    labels = ["Data (de)", "Data (ate)", "Estado", "Motorista", "Cliente / contato / n"]
    placeholders = ["__/__/____", "__/__/____", "TODOS OS ESTADOS", "TODOS", "PESQUISAR..."]
    for index, label in enumerate(labels):
        tk.Label(box, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 8)).grid(row=1, column=index, sticky="w", padx=12)
        entry = tk.Entry(box, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9), width=22)
        entry.grid(row=2, column=index, sticky="ew", padx=12, pady=(3, 12))
        box.grid_columnconfigure(index, weight=1)
        if index < 2:
            setup_date_mask(entry)
        else:
            apply_input_rules(entry, placeholder=placeholders[index], label=label)


def render_reservation_table(parent, app):
    _, table = table_scroll_host(parent)
    weights = [0, 2, 2, 1, 3, 1, 2, 1, 1, 0]
    minsizes = [50, 0, 0, 0, 0, 0, 0, 0, 0, 340]
    headers = ["N", "Cliente", "Contato", "Tipo", "Trajeto", "Data", "Motorista", "Valor", "Status", "Acoes"]
    grid_table_header(table, headers, weights, minsizes)

    for row_index, reservation in enumerate(app.reservations, start=1):
        add_reservation_row(table, app, reservation, row_index)


def add_reservation_row(table, app, reservation, row_index):
    bg = COLORS["panel"] if row_index % 2 else "#FAFBFD"
    values = [
        reservation["numero"],
        reservation["cliente"],
        f'{reservation["contato"]} · {reservation["email"]}',
        reservation["tipo"],
        reservation["trajeto"],
        reservation["data"],
        reservation["motorista"],
        reservation["valor"],
        reservation["status"],
    ]

    trunc = [None, 22, 28, 14, 36, 14, 18, None, None]
    for col, value in enumerate(values):
        grid_table_cell(table, row_index, col, value, bg, truncate=trunc[col])

    actions = tk.Frame(table, bg=bg)
    actions.grid(row=row_index, column=9, sticky="ew", padx=4, pady=4)
    render_action_buttons(
        actions,
        [
            ("Editar", lambda: open_edit_reservation_form(app, reservation)),
            ("Ver", lambda: view_reservation(app, reservation)),
            ("Baixar", lambda: download_reservation(app, reservation)),
            ("Excluir", lambda: delete_reservation(app, reservation)),
        ],
        bg=bg,
    )


def open_edit_reservation_form(app, reservation):
    window = tk.Toplevel(app)
    window.title("Editar Reserva")
    window.configure(bg=COLORS["bg"])
    window.geometry("460x470")
    window.resizable(False, False)
    window.transient(app)
    window.grab_set()

    form = tk.Frame(window, bg=COLORS["panel"], highlightthickness=1, highlightbackground="#D3DAE3")
    form.pack(fill="both", expand=True, padx=14, pady=14)

    tk.Label(form, text="EDITAR RESERVA", bg=COLORS["panel"], fg=COLORS["primary"], font=("Segoe UI Semibold", 12)).pack(anchor="w", padx=12, pady=(12, 8))

    entries = {}
    for key, label in FIELDS:
        line = tk.Frame(form, bg=COLORS["panel"])
        line.pack(fill="x", padx=12, pady=4)
        tk.Label(line, text=label, bg=COLORS["panel"], fg=COLORS["muted"], width=10, anchor="w", font=("Segoe UI Semibold", 9)).pack(side="left")
        entry = tk.Entry(line, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
        entry.pack(side="left", fill="x", expand=True)
        if key == "data":
            setup_date_mask(entry, initial_value=reservation.get(key, ""))
        else:
            entry.insert(0, str(reservation.get(key, "") or "").upper())
        entries[key] = entry

    footer = tk.Frame(form, bg=COLORS["panel"])
    footer.pack(fill="x", padx=12, pady=(14, 8))
    styled_button(footer, "Cancelar", style="secondary", command=window.destroy).pack(side="right")
    styled_button(footer, "Salvar", style="success", command=lambda: save_edit_reservation(app, window, entries, reservation)).pack(side="right", padx=(0, 8))


def open_create_reservation_form(app):
    window = tk.Toplevel(app)
    window.title("Criar Nova Reserva")
    window.configure(bg=COLORS["bg"])
    window.geometry("820x720")
    window.minsize(760, 620)
    window.transient(app)
    window.grab_set()

    footer = tk.Frame(window, bg=COLORS["bg"])
    footer.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
    styled_button(footer, "Cancelar", style="secondary", command=window.destroy).pack(side="right")
    styled_button(footer, "Criar Reserva", style="success", size="lg", command=lambda: save_new_reservation(app, window, fields, po_controls)).pack(side="right", padx=(0, 8))

    shell = tk.Frame(window, bg=COLORS["bg"])
    shell.pack(fill="both", expand=True, padx=10, pady=(10, 0))

    canvas = tk.Canvas(shell, bg=COLORS["bg"], highlightthickness=0)
    scrollbar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    form = tk.Frame(canvas, bg=COLORS["panel"], highlightthickness=1, highlightbackground="#D3DAE3")
    canvas_window = canvas.create_window((0, 0), window=form, anchor="nw")

    fields = {}
    po_controls = {}
    client_mode = tk.StringVar(value="novo")
    selected_client = tk.StringVar()

    header = tk.Frame(form, bg=COLORS["panel"])
    header.pack(fill="x", padx=18, pady=(16, 12))
    tk.Label(header, text="Criar Nova Reserva", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 18)).pack(anchor="w")
    tk.Label(header, text="Preencha os dados para criar uma nova reserva manual.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

    def resize_form(event):
        canvas.itemconfigure(canvas_window, width=max(event.width - 6, 720))

    def mouse_scroll(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    form.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", resize_form)
    canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", mouse_scroll))
    canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
    window.bind("<Destroy>", lambda _event: canvas.unbind_all("<MouseWheel>"))

    client_section = section(form, "Informacoes do Cliente")
    tk.Label(client_section, text="Origem do cliente", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 3), columnspan=2)

    mode_line = tk.Frame(client_section, bg=COLORS["panel"])
    mode_line.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8), columnspan=2)
    tk.Radiobutton(mode_line, text="Cliente cadastrado", variable=client_mode, value="cadastrado", bg=COLORS["panel"], fg=COLORS["text"], selectcolor=COLORS["panel"], activebackground=COLORS["panel"], command=lambda: update_client_origin()).pack(side="left", padx=(0, 14))
    tk.Radiobutton(mode_line, text="NOVO CLIENTE", variable=client_mode, value="novo", bg=COLORS["panel"], fg=COLORS["text"], selectcolor=COLORS["panel"], activebackground=COLORS["panel"], command=lambda: update_client_origin()).pack(side="left")

    selector_box = tk.Frame(client_section, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground="#D3DAE3")
    selector_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))
    tk.Label(selector_box, text="Pesquisar cliente cadastrado", bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=8, pady=(7, 2))
    client_search = tk.Entry(selector_box, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
    client_search.pack(fill="x", padx=8, pady=(0, 5))
    clients = registered_clients(app)
    client_combo = ttk.Combobox(selector_box, textvariable=selected_client, values=[item["nome"] for item in clients], state="readonly")
    client_combo.pack(fill="x", padx=8, pady=(0, 8))

    manual_client_box = tk.Frame(client_section, bg=COLORS["panel"])
    manual_client_box.grid(row=3, column=0, columnspan=2, sticky="ew")
    manual_client_box.grid_columnconfigure(1, weight=1)
    add_input(manual_client_box, fields, "nome", "Nome Completo *", 0, placeholder="")
    add_input(manual_client_box, fields, "documento", "CPF/CNPJ *", 1, placeholder="")
    add_input(manual_client_box, fields, "email", "Email *", 2, placeholder="")
    add_input(manual_client_box, fields, "telefone", "Telefone *", 3, placeholder="")

    trip_section = section(form, "Detalhes da Viagem")
    tk.Label(
        trip_section,
        text="Indique enderecos completos ou ative PO para selecionar pontos operacionais cadastrados em Abrangencia.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
    ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 7), columnspan=2)

    trip_type = add_combo(trip_section, fields, "tipo", "Tipo de Viagem *", 1, ["Somente Ida", "Ida e Volta", "Por Hora"], default="Somente Ida")

    ida_section = section(form, "-> Ida")
    add_po_address_field(ida_section, fields, po_controls, "embarque", "Local de Embarque (IDA) *", 0, app, placeholder="Endereco completo de embarque")
    add_po_address_field(ida_section, fields, po_controls, "desembarque", "Local de Desembarque (IDA) *", 1, app, placeholder="Endereco completo de destino")
    add_input(ida_section, fields, "data", "Data do Embarque (IDA) *", 2, placeholder="dd/mm/aaaa")
    add_input(ida_section, fields, "hora", "Hora do Embarque (IDA) *", 3, placeholder="--:--")
    add_input(ida_section, fields, "passageiros", "Passageiros", 4, placeholder="")
    add_input(ida_section, fields, "cupom", "Cupom", 5, placeholder="")
    add_text(ida_section, fields, "mensagem", "Mensagem / Observacoes", 6)

    volta_section = section(form, "<-> Volta")
    add_po_address_field(volta_section, fields, po_controls, "volta_embarque", "Local de Embarque (Volta)", 0, app, placeholder="Endereco completo")
    add_po_address_field(volta_section, fields, po_controls, "volta_desembarque", "Local de Desembarque (Volta)", 1, app, placeholder="Endereco completo")
    add_input(volta_section, fields, "volta_data", "Data da Volta *", 2, placeholder="dd/mm/aaaa")
    add_input(volta_section, fields, "volta_hora", "Hora da Volta *", 3, placeholder="--:--")
    add_input(volta_section, fields, "volta_passageiros", "Passageiros", 4, placeholder="")
    add_input(volta_section, fields, "volta_cupom", "Cupom", 5, placeholder="")
    add_text(volta_section, fields, "volta_mensagem", "Mensagem / Observacoes", 6)

    hora_section = section(form, "Por Hora")
    add_po_address_field(hora_section, fields, po_controls, "hora_inicio", "Endereco de Inicio", 0, app, placeholder="Endereco completo")
    add_po_address_field(hora_section, fields, po_controls, "hora_fim", "Ponto de Encerramento", 1, app, placeholder="Endereco completo")
    add_input(hora_section, fields, "hora_data", "Data *", 2, placeholder="dd/mm/aaaa")
    add_input(hora_section, fields, "hora_horario", "Hora de inicio *", 3, placeholder="--:--")
    add_input(hora_section, fields, "hora_passageiros", "Passageiros", 4, placeholder="")
    add_input(hora_section, fields, "qtd_horas", "Qtd. Horas", 5, placeholder="")
    add_input(hora_section, fields, "hora_cupom", "Cupom", 6, placeholder="")
    add_text(hora_section, fields, "hora_observacoes", "Itinerario / Observacoes", 7)

    driver_section = section(form, "Veiculo e Motorista")
    add_combo(driver_section, fields, "quem_faz", "Quem fara a viagem? *", 0, ["Motorista"], default="Motorista")
    add_combo(driver_section, fields, "motorista", "Motorista da frota *", 1, ["-- Nao atribuir ainda --"] + registered_drivers(app), default="-- Nao atribuir ainda --")
    tk.Label(
        driver_section,
        text="So aparecem motoristas com portal ativo (definiram senha pelo link). Atribua a reserva para ela surgir na agenda dele.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 8),
        wraplength=650,
        justify="left",
    ).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10), columnspan=2)

    payment_section = section(form, "Valores e Pagamento")
    add_input(payment_section, fields, "valor_base", "Valor Base *", 0, placeholder="0")
    add_input(payment_section, fields, "desconto", "Desconto (%)", 1, placeholder="0")
    add_input(payment_section, fields, "pagamento", "Metodo de Pagamento", 2, placeholder="Ex: Dinheiro, Cartao, PIX")
    total_label = add_total_label(payment_section, "Valor Total (a receber do cliente)", 3)
    add_combo(payment_section, fields, "status", "Status da reserva", 4, ["Pendente", "Confirmada", "Concluida", "Cancelada"], default="Pendente")
    tk.Label(
        payment_section,
        text="Com repasse > 0, ao salvar registra automaticamente em Financeiro > Contas a pagar (Repasse motorista).",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 8),
        wraplength=650,
        justify="left",
    ).grid(row=5, column=0, sticky="w", padx=12, pady=(0, 7), columnspan=2)
    add_input(payment_section, fields, "repasse", "Repasse ao motorista (R$)", 6, placeholder="0,00")
    repasse_info = tk.Label(
        payment_section,
        text="",
        bg=COLORS["panel_alt"],
        fg=COLORS["primary"],
        font=("Segoe UI Semibold", 9),
        anchor="w",
        padx=8,
        pady=6,
        wraplength=650,
        justify="left",
    )
    repasse_info.grid(row=7, column=0, sticky="ew", padx=12, pady=(0, 8), columnspan=2)
    tk.Label(
        payment_section,
        text="Valor a pagar ao motorista apos a viagem concluida (margem = total - repasse).",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 8),
    ).grid(row=8, column=0, sticky="w", padx=12, pady=(0, 8), columnspan=2)
    add_text(payment_section, fields, "observacoes", "Observacoes", 9, placeholder="Observacoes adicionais sobre a reserva...")

    def refresh_total(_event=None):
        total = calculate_total_amount(fields["valor_base"], fields["desconto"])
        total_label.configure(text=format_amount(total))

    def refresh_repasse_info(_event=None):
        repasse_value = parse_amount(field_value(fields["repasse"]))
        motorista = field_value(fields["motorista"]) or "-"
        if repasse_value > 0:
            repasse_info.configure(
                text=(
                    f"Conta a pagar: REPASSE MOTORISTA  ·  {motorista}  ·  "
                    f"{format_amount(repasse_value)}  ·  Financeiro > Contas a pagar"
                )
            )
        else:
            repasse_info.configure(text="")

    for widget in (fields["valor_base"], fields["desconto"]):
        widget.bind("<KeyRelease>", refresh_total)
    fields["repasse"].bind("<KeyRelease>", refresh_repasse_info)
    fields["motorista"].bind("<<ComboboxSelected>>", refresh_repasse_info)
    refresh_total()
    refresh_repasse_info()

    def fill_registered_client(_event=None):
        client = find_client(clients, selected_client.get())
        if not client:
            return
        set_input_value(fields["nome"], client["nome"])
        set_input_value(fields["telefone"], client["telefone"])
        set_input_value(fields["email"], client["email"])
        set_input_value(fields["documento"], client["documento"])

    def filter_clients(_event=None):
        search = client_search.get().strip().lower()
        names = [item["nome"] for item in clients if search in item["nome"].lower()]
        client_combo.configure(values=names)
        if names:
            client_combo.set(names[0])
            fill_registered_client()

    client_search.bind("<KeyRelease>", filter_clients)
    client_combo.bind("<<ComboboxSelected>>", fill_registered_client)

    def update_client_origin():
        if client_mode.get() == "cadastrado":
            selector_box.grid()
            manual_client_box.grid_remove()
            if not selected_client.get() and clients:
                selected_client.set(clients[0]["nome"])
                fill_registered_client()
            return

        selector_box.grid_remove()
        manual_client_box.grid()

    def update_trip_type(_event=None):
        selected = fields["tipo"].get()
        if selected == "Ida e Volta":
            ida_section.section_box.pack(fill="x", padx=16, pady=(0, 12), before=driver_section.section_box)
            volta_section.section_box.pack(fill="x", padx=16, pady=(0, 12), before=driver_section.section_box)
            hora_section.section_box.pack_forget()
        elif selected == "Por Hora":
            ida_section.section_box.pack_forget()
            volta_section.section_box.pack_forget()
            hora_section.section_box.pack(fill="x", padx=16, pady=(0, 12), before=driver_section.section_box)
        else:
            ida_section.section_box.pack(fill="x", padx=16, pady=(0, 12), before=driver_section.section_box)
            volta_section.section_box.pack_forget()
            hora_section.section_box.pack_forget()
        canvas.configure(scrollregion=canvas.bbox("all"))

    trip_type.bind("<<ComboboxSelected>>", update_trip_type)
    update_client_origin()
    update_trip_type()


def section(parent, title):
    box = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground="#D3DAE3")
    box.pack(fill="x", padx=16, pady=(0, 12))
    tk.Label(box, text=title, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 11)).pack(anchor="w", padx=12, pady=(10, 0))
    content = tk.Frame(box, bg=COLORS["panel"])
    content.pack(fill="x", pady=(2, 8))
    content.grid_columnconfigure(1, weight=1)
    content.section_box = box
    return content


def add_input(parent, fields, key, label, row, placeholder=""):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).grid(row=row, column=0, sticky="w", padx=12, pady=5)
    entry = tk.Entry(parent, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
    entry.grid(row=row, column=1, sticky="ew", padx=12, pady=5)
    apply_input_rules(entry, field_key=key, placeholder=placeholder, label=label)
    fields[key] = entry
    return entry


def add_combo(parent, fields, key, label, row, values, default=""):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).grid(row=row, column=0, sticky="w", padx=12, pady=5)
    combo = ttk.Combobox(parent, values=values, state="readonly", font=("Segoe UI", 9))
    combo.grid(row=row, column=1, sticky="ew", padx=12, pady=5)
    combo.set(default or (values[0] if values else ""))
    fields[key] = combo
    return combo


def add_text(parent, fields, key, label, row, placeholder=""):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).grid(row=row, column=0, sticky="nw", padx=12, pady=5)
    text = tk.Text(parent, height=3, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9), wrap="word")
    text.grid(row=row, column=1, sticky="ew", padx=12, pady=5)
    if placeholder:
        setup_placeholder(text, placeholder.upper())
    fields[key] = text
    return text


def add_total_label(parent, label, row):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).grid(row=row, column=0, sticky="w", padx=12, pady=5)
    value_label = tk.Label(parent, text="R$ 0,00", bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 10), anchor="w", padx=8, pady=5)
    value_label.grid(row=row, column=1, sticky="ew", padx=12, pady=5)
    return value_label


def calculate_total_amount(valor_base_widget, desconto_widget):
    base = parse_amount(field_value(valor_base_widget))
    discount = parse_amount(field_value(desconto_widget))
    discount = min(max(discount, 0), 100)
    return round(base * (1 - discount / 100), 2)


def finance_payable_account(reservation_number, motorista):
    clean = str(reservation_number or "").replace("#", "")
    return f"CP-REPASSE-{clean or '0000'}"


def apply_finance_fields(payload, motorista):
    repasse_value = parse_amount(payload.get("repasse"))
    if repasse_value > 0:
        account = finance_payable_account(payload.get("numero"), motorista)
        payload["conta_pagar"] = account
        payload["conta_pagar_descricao"] = f"Repasse motorista — {motorista} — Reserva {payload.get('numero', '')}"
    else:
        payload["conta_pagar"] = ""
        payload["conta_pagar_descricao"] = ""
    return payload


def add_readonly(parent, label, value, row):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).grid(row=row, column=0, sticky="w", padx=12, pady=5)
    tk.Label(parent, text=value, bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 10), anchor="w", padx=8, pady=5).grid(row=row, column=1, sticky="ew", padx=12, pady=5)


def field_value(widget):
    if isinstance(widget, ttk.Combobox):
        return widget.get().strip()
    return resolve_widget_value(widget)


def registered_clients(app):
    clients = []
    for client in getattr(app, "clients", []) or []:
        nome = str(client.get("nome") or client.get("razao_social") or client.get("empresa") or "").strip()
        if not nome:
            continue
        clients.append(
            {
                "id": client.get("id", ""),
                "nome": nome,
                "telefone": client.get("telefone", ""),
                "email": client.get("email", ""),
                "documento": client.get("cpf") or client.get("cnpj") or client.get("documento", ""),
            }
        )
    return clients


def registered_drivers(app):
    labels = []
    for driver in active_portal_drivers(app):
        label = f'{driver.get("nome", "")} ({driver.get("id", "")})'
        labels.append(label)
    return labels


def resolve_driver_assignment(app, motorista_label):
    motorista_label = str(motorista_label or "").strip()
    if not motorista_label or motorista_label == "-- Nao atribuir ainda --":
        return "-", ""
    name = motorista_label.split(" (drv-")[0].strip()
    if "(drv-" in motorista_label:
        driver_id = motorista_label.rsplit("(", 1)[1].rstrip(")")
    else:
        driver = find_driver_by_name(app, name)
        driver_id = driver.get("id", "") if driver else ""
    return name or motorista_label, driver_id


def find_client(clients, name):
    for client in clients:
        if client["nome"] == name:
            return client
    return None


def default_value(key):
    defaults = {
        "tipo": "Somente Ida",
        "data": "01/06/2026",
        "motorista": "-",
        "valor": "R$ 0,00",
        "status": "Pendente",
    }
    return defaults.get(key, "")


def save_edit_reservation(app, window, entries, reservation):
    values = {key: entry.get().strip() for key, entry in entries.items()}
    if not values["cliente"]:
        messagebox.showwarning("Campo obrigatorio", "Informe o cliente da reserva.")
        return

    reservation.update(values)
    app.save_state()
    window.destroy()
    app.show_page("RESERVAS")


def _reservation_location_meta(values, embarque_key, desembarque_key=None):
    meta = {
        f"{embarque_key}_po_id": values.get(f"{embarque_key}_po_id", ""),
        f"{embarque_key}_modo": values.get(f"{embarque_key}_modo", "manual"),
    }
    if desembarque_key:
        meta[f"{desembarque_key}_po_id"] = values.get(f"{desembarque_key}_po_id", "")
        meta[f"{desembarque_key}_modo"] = values.get(f"{desembarque_key}_modo", "manual")
    return meta


def save_new_reservation(app, window, fields, po_controls=None):
    po_controls = po_controls or {}
    values = {key: field_value(widget) for key, widget in fields.items()}
    address_keys = ["embarque", "desembarque", "volta_embarque", "volta_desembarque", "hora_inicio", "hora_fim"]
    values.update(collect_address_values(po_controls, address_keys))
    required = {
        "nome": "Nome Completo",
        "documento": "CPF/CNPJ",
        "email": "Email",
        "telefone": "Telefone",
        "valor_base": "Valor Base",
    }

    if values.get("tipo") == "Por Hora":
        required.update(
            {
                "hora_inicio": "Endereco de Inicio",
                "hora_fim": "Ponto de Encerramento",
                "hora_data": "Data",
                "hora_horario": "Hora de inicio",
                "hora_passageiros": "Passageiros",
                "qtd_horas": "Qtd. Horas",
            }
        )
    else:
        required.update(
            {
                "embarque": "Local de Embarque",
                "desembarque": "Local de Desembarque",
                "data": "Data do Embarque",
                "hora": "Hora do Embarque",
                "passageiros": "Passageiros",
            }
        )
        if values.get("tipo") == "Ida e Volta":
            required.update(
                {
                    "volta_embarque": "Local de Embarque (Volta)",
                    "volta_desembarque": "Local de Desembarque (Volta)",
                    "volta_data": "Data da Volta",
                    "volta_hora": "Hora da Volta",
                }
            )

    for key, label in required.items():
        if not values.get(key):
            messagebox.showwarning("Campo obrigatorio", f"Informe: {label}.", parent=window)
            return

    ok, msg = validate_email_field(fields["email"], parent=window, label="Email")
    if not ok:
        messagebox.showwarning("Email invalido", msg, parent=window)
        return

    if not values.get("documento") or len(values["documento"]) < 11:
        messagebox.showwarning("Documento invalido", "Informe um CPF (11 digitos) ou CNPJ (14 digitos) valido.", parent=window)
        return

    if len(values.get("telefone", "")) < 10:
        messagebox.showwarning("Telefone invalido", "Informe um telefone completo no formato (XX) X XXXX-XXXX.", parent=window)
        return

    trip_type = values.get("tipo", "Somente Ida")
    if trip_type == "Por Hora":
        ok, msg = validate_future_datetime(values.get("hora_data"), values.get("hora_horario"), label="Data/hora do servico")
        if not ok:
            messagebox.showwarning("Data/hora invalida", msg, parent=window)
            return
    else:
        ok, msg = validate_future_datetime(values.get("data"), values.get("hora"), label="Data/hora de embarque (IDA)")
        if not ok:
            messagebox.showwarning("Data/hora invalida", msg, parent=window)
            return
        if trip_type == "Ida e Volta":
            ok, msg = validate_future_datetime(values.get("volta_data"), values.get("volta_hora"), label="Data/hora de embarque (VOLTA)")
            if not ok:
                messagebox.showwarning("Data/hora invalida", msg, parent=window)
                return
            ida_dt = parse_br_datetime(values.get("data"), values.get("hora"))
            volta_dt = parse_br_datetime(values.get("volta_data"), values.get("volta_hora"))
            if ida_dt and volta_dt and volta_dt < ida_dt:
                messagebox.showwarning("Data/hora invalida", "A volta nao pode ser anterior a ida.", parent=window)
                return

    total_value = calculate_total_amount(fields["valor_base"], fields["desconto"])
    valor = format_amount(total_value)
    repasse_total = parse_amount(values.get("repasse"))
    motorista, driver_id = resolve_driver_assignment(app, values.get("motorista"))

    common = {
        "cliente": values["nome"],
        "contato": values["telefone"],
        "email": values["email"],
        "motorista": motorista,
        "driver_id": driver_id,
        "valor": valor,
        "valor_base": values.get("valor_base", ""),
        "desconto": values.get("desconto", "0"),
        "status": values["status"],
        "documento": values["documento"],
        "pagamento": values.get("pagamento", ""),
        "repasse": values.get("repasse", "0,00"),
    }

    created = []
    repasse_ida = repasse_total
    repasse_volta = 0.0
    if trip_type == "Ida e Volta" and repasse_total > 0:
        repasse_ida = round(repasse_total / 2, 2)
        repasse_volta = round(repasse_total - repasse_ida, 2)

    if trip_type == "Ida e Volta":
        pair_id = f"pair-{len(app.reservations) + 1:04d}"
        ida_num, volta_num = next_reservation_numbers(app, 2)
        ida_data = values["data"]
        if values.get("hora"):
            ida_data = f"{ida_data} {values['hora']}"
        volta_data = values["volta_data"]
        if values.get("volta_hora"):
            volta_data = f"{volta_data} {values['volta_hora']}"

        ida_res = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "embarque", "desembarque"),
                "numero": ida_num,
                "tipo": "Ida",
                "trajeto": f'{values["embarque"]} -> {values["desembarque"]}',
                "data": ida_data,
                "hora": values.get("hora", ""),
                "passageiros": values["passageiros"],
                "repasse": format_amount(repasse_ida) if repasse_ida > 0 else "0,00",
                "observacoes": "\n".join(filter(None, [values.get("observacoes", ""), values.get("mensagem", "")])).strip(),
                "par_id": pair_id,
                "perna": "ida",
            },
            motorista,
        )
        volta_res = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "volta_embarque", "volta_desembarque"),
                "numero": volta_num,
                "tipo": "Volta",
                "trajeto": f'{values["volta_embarque"]} -> {values["volta_desembarque"]}',
                "data": volta_data,
                "hora": values.get("volta_hora", ""),
                "passageiros": values.get("volta_passageiros") or values["passageiros"],
                "repasse": format_amount(repasse_volta) if repasse_volta > 0 else "0,00",
                "observacoes": "\n".join(filter(None, [values.get("observacoes", ""), values.get("volta_mensagem", "")])).strip(),
                "par_id": pair_id,
                "perna": "volta",
            },
            motorista,
        )
        app.reservations.insert(0, volta_res)
        app.reservations.insert(0, ida_res)
        created.extend([ida_res, volta_res])
    elif values["tipo"] == "Por Hora":
        reservation = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "hora_inicio", "hora_fim"),
                "numero": next_reservation_number(app),
                "tipo": values["tipo"],
                "trajeto": f'{values["hora_inicio"]} -> {values["hora_fim"]}',
                "data": values["hora_data"],
                "hora": values.get("hora_horario", ""),
                "passageiros": values["hora_passageiros"],
                "observacoes": values.get("hora_observacoes", ""),
            },
            motorista,
        )
        app.reservations.insert(0, reservation)
        created.append(reservation)
    else:
        data = values["data"]
        hora = values.get("hora", "")
        if hora:
            data = f"{data} {hora}"
        reservation = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "embarque", "desembarque"),
                "numero": next_reservation_number(app),
                "tipo": values["tipo"],
                "trajeto": f'{values["embarque"]} -> {values["desembarque"]}',
                "data": data,
                "hora": hora,
                "passageiros": values["passageiros"],
                "observacoes": "\n".join(filter(None, [values.get("observacoes", ""), values.get("mensagem", "")])).strip(),
            },
            motorista,
        )
        app.reservations.insert(0, reservation)
        created.append(reservation)

    app.save_state()
    window.destroy()
    app.show_page("RESERVAS")

    payable_lines = [
        f'{item["conta_pagar"]}: {item["conta_pagar_descricao"]} ({item.get("repasse", "")})'
        for item in created
        if parse_amount(item.get("repasse")) > 0
    ]
    if payable_lines:
        messagebox.showinfo(
            "Financeiro — Contas a pagar",
            "Conta(s) registrada(s) automaticamente:\n\n" + "\n".join(payable_lines) + "\n\nVeja em Financeiro > Contas a pagar.",
            parent=app,
        )


def view_reservation(app, reservation):
    details = "\n".join(
        [
            f'Numero: {reservation["numero"]}',
            f'Cliente: {reservation["cliente"]}',
            f'Contato: {reservation["contato"]}',
            f'E-mail: {reservation["email"]}',
            f'Tipo: {reservation["tipo"]}',
            f'Trajeto: {reservation["trajeto"]}',
            f'Data: {reservation["data"]}',
            f'Motorista: {reservation["motorista"]}',
            f'Valor: {reservation["valor"]}',
            f'Status: {reservation["status"]}',
        ]
    )
    messagebox.showinfo("Reserva", details, parent=app)


def download_reservation(app, reservation):
    window = tk.Toplevel(app)
    window.title("Baixar reserva")
    window.configure(bg=COLORS["bg"])
    window.geometry("460x360")
    window.resizable(False, False)
    window.transient(app)
    window.grab_set()

    shell = tk.Frame(window, bg=COLORS["panel"], highlightthickness=1, highlightbackground="#D3DAE3")
    shell.pack(fill="both", expand=True, padx=16, pady=16)
    tk.Label(shell, text="Escolha a via do PDF", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 14)).pack(anchor="w", padx=16, pady=(16, 4))
    tk.Label(
        shell,
        text=f'Reserva {reservation.get("numero", "")} — {reservation.get("cliente", "")}',
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
    ).pack(anchor="w", padx=16, pady=(0, 12))

    options = [
        ("cliente", "Via do Cliente", "Trajeto, valores e pagamento. Oculta repasse e dados internos."),
        ("motorista", "Via do Motorista", "Operacao e contato. Oculta CPF/e-mail e valor cobrado do cliente."),
        ("loja", "Via da Loja", "Documento completo com repasse, financeiro e todos os dados."),
    ]
    for via, title, hint in options:
        row = tk.Frame(shell, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
        row.pack(fill="x", padx=16, pady=6)
        text_box = tk.Frame(row, bg=COLORS["panel_alt"])
        text_box.pack(side="left", fill="x", expand=True, padx=12, pady=10)
        tk.Label(text_box, text=title, bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
        tk.Label(text_box, text=hint, bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 8), wraplength=280, justify="left").pack(anchor="w", pady=(2, 0))
        styled_button(row, "Gerar PDF", style="primary", size="sm", command=lambda v=via: _export_reservation_pdf(app, reservation, v, window)).pack(side="right", padx=12, pady=10)

    styled_button(shell, "Fechar", style="secondary", command=window.destroy).pack(pady=(8, 16))


def _export_reservation_pdf(app, reservation, via, modal):
    default_name = default_pdf_filename(reservation, via)
    target = filedialog.asksaveasfilename(
        parent=modal,
        title="Salvar PDF da reserva",
        defaultextension=".pdf",
        initialfile=default_name,
        filetypes=[("PDF", "*.pdf")],
    )
    if not target:
        return
    try:
        generate_reservation_pdf(reservation, app, via, target)
    except Exception as exc:
        messagebox.showerror("Baixar", f"Nao foi possivel gerar o PDF:\n{exc}", parent=modal)
        return
    modal.destroy()
    messagebox.showinfo("Baixar", f"PDF gerado com sucesso:\n{target}", parent=app)


def delete_reservation(app, reservation):
    confirmed = messagebox.askyesno(
        "Confirmar exclusao",
        f'Deseja excluir a reserva {reservation["numero"]}?',
        parent=app,
    )
    if not confirmed:
        return

    app.reservations.remove(reservation)
    app.save_state()
    app.show_page("RESERVAS")
