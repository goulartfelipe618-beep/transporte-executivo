import calendar
import os
import struct
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

from .components import apply_input_rules, data_table, header_panel, resolve_widget_value, settings_grid, setup_date_mask, setup_placeholder, summary_cards
from .data import (
    ABRANGENCIA,
    REGISTRY_PAGES,
    SYSTEM_AUTOMATIONS,
    SYSTEM_CONFIG,
    TRANSFER_COLUMNS,
    TRANSFER_PAGES,
)
from .portal_auth import (
    driver_has_password,
    generate_activation_token,
    normalize_driver_record,
)
from .portal_server import driver_key, start_driver_portal_server
from .repository.ids import next_entity_id
from .vehicles_model import (
    VEHICLE_OPERATIONAL_FIELDS,
    VEHICLE_TYPES,
    apply_network_flags,
    is_network_vehicle,
    normalize_vehicle_type,
)
from .table_ui import grid_table_cell, grid_table_header, render_action_buttons, table_scroll_host
from .theme import COLORS, FONTS, panel_frame, styled_button


MONTH_NAMES = [
    "",
    "Janeiro",
    "Fevereiro",
    "Marco",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

WEEKDAY_NAMES = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SAB"]

AGENDA_COLORS = {
    "bg": COLORS["bg"],
    "panel": COLORS["panel"],
    "panel_alt": COLORS["panel_alt"],
    "header": COLORS["primary"],
    "header_text": COLORS["white"],
    "cell": COLORS["panel"],
    "cell_other": "#F1F5F9",
    "cell_hover": COLORS["primary_soft"],
    "line": COLORS["line"],
    "text": COLORS["text"],
    "muted": COLORS["muted"],
    "accent": COLORS["primary"],
    "accent_soft": COLORS["primary_soft"],
    "today_ring": COLORS["primary"],
    "green": COLORS["success"],
    "danger": COLORS["danger"],
}


def render_standard_page(parent, page_data):
    title, subtitle, action = page_data["header"]
    header_panel(parent, title, subtitle, action)
    summary_cards(parent, page_data["cards"])
    data_table(parent, page_data["columns"], page_data["rows"])


def render_abrangencia(parent, app):
    from .coverage_ui import render_abrangencia as render_abrangencia_page

    render_abrangencia_page(parent, app)


def render_agenda(parent, app):
    if not hasattr(app, "agenda_month"):
        app.agenda_month = date.today().replace(day=1)

    parent.configure(bg=AGENDA_COLORS["bg"])
    render_agenda_header(parent, app)
    render_calendar(parent, app)


def render_agenda_header(parent, app):
    header = tk.Frame(parent, bg=AGENDA_COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))

    left = tk.Frame(header, bg=AGENDA_COLORS["bg"])
    left.pack(side="left", fill="x", expand=True)

    tk.Label(
        left,
        text="Agenda",
        bg=AGENDA_COLORS["bg"],
        fg=AGENDA_COLORS["text"],
        font=("Segoe UI Semibold", 20),
    ).pack(anchor="w")
    tk.Label(
        left,
        text="Calendario com as reservas programadas. Clique em uma reserva para ver todos os detalhes.",
        bg=AGENDA_COLORS["bg"],
        fg=AGENDA_COLORS["muted"],
        font=("Segoe UI", 9),
        wraplength=640,
        justify="left",
    ).pack(anchor="w", pady=(2, 0))

    actions = tk.Frame(header, bg=AGENDA_COLORS["bg"])
    actions.pack(side="right", anchor="n")
    agenda_button(actions, "Atualizar", lambda: app.show_page("AGENDA"), style="secondary").pack(side="left", padx=(0, 8))
    agenda_button(actions, "Hoje", lambda: go_to_today(app), style="primary").pack(side="left")


def render_calendar(parent, app):
    month = app.agenda_month
    reservations_by_day = group_reservations_by_day(app.reservations)

    shell = tk.Frame(parent, bg=AGENDA_COLORS["panel"], highlightthickness=1, highlightbackground=AGENDA_COLORS["line"])
    shell.pack(fill="both", expand=True)

    toolbar = tk.Frame(shell, bg=AGENDA_COLORS["header"])
    toolbar.pack(fill="x")

    nav = tk.Frame(toolbar, bg=AGENDA_COLORS["header"])
    nav.pack(side="left", padx=16, pady=14)
    for symbol, delta in (("◀", -1), ("▶", 1)):
        tk.Button(
            nav,
            text=symbol,
            command=lambda d=delta: change_agenda_month(app, d),
            bg="#1D4ED8",
            fg=AGENDA_COLORS["header_text"],
            activebackground="#1E40AF",
            activeforeground=AGENDA_COLORS["header_text"],
            bd=0,
            relief="flat",
            font=("Segoe UI Semibold", 11),
            width=3,
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))

    tk.Label(
        toolbar,
        text=f"{MONTH_NAMES[month.month].upper()} · {month.year}",
        bg=AGENDA_COLORS["header"],
        fg=AGENDA_COLORS["header_text"],
        font=("Segoe UI Semibold", 16),
    ).pack(side="left", expand=True)

    total_month = sum(
        1
        for item in app.reservations
        if parse_reservation_date(item)
        and parse_reservation_date(item).month == month.month
        and parse_reservation_date(item).year == month.year
    )
    stats = tk.Frame(toolbar, bg=AGENDA_COLORS["header"])
    stats.pack(side="right", padx=16, pady=12)
    tk.Label(stats, text=f"{total_month}", bg=AGENDA_COLORS["header"], fg=AGENDA_COLORS["header_text"], font=("Segoe UI Semibold", 18)).pack(side="left")
    tk.Label(stats, text="  reservas no mes", bg=AGENDA_COLORS["header"], fg="#BFDBFE", font=("Segoe UI", 9)).pack(side="left")

    calendar_box = tk.Frame(shell, bg=AGENDA_COLORS["panel_alt"], padx=10, pady=10)
    calendar_box.pack(fill="both", expand=True)

    for column, label in enumerate(WEEKDAY_NAMES):
        calendar_box.grid_columnconfigure(column, weight=1, uniform="agenda_days")
        tk.Label(
            calendar_box,
            text=label.upper(),
            bg=AGENDA_COLORS["accent_soft"],
            fg=AGENDA_COLORS["accent"],
            font=("Segoe UI Semibold", 9),
            pady=10,
        ).grid(row=0, column=column, sticky="ew", padx=3, pady=(0, 6))

    weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(month.year, month.month)
    for row_index, week in enumerate(weeks, start=1):
        calendar_box.grid_rowconfigure(row_index, weight=1, uniform="agenda_rows")
        for column, day in enumerate(week):
            day_reservations = reservations_by_day.get(day, [])
            add_calendar_day(calendar_box, app, day, month, day_reservations, row_index, column)


def add_calendar_day(parent, app, day, active_month, reservations, row, column):
    is_current_month = day.month == active_month.month
    is_today = day == date.today()
    bg = AGENDA_COLORS["cell"] if is_current_month else AGENDA_COLORS["cell_other"]
    border = AGENDA_COLORS["today_ring"] if is_today else AGENDA_COLORS["line"]
    border_width = 2 if is_today else 1

    cell = tk.Frame(
        parent,
        bg=bg,
        highlightthickness=border_width,
        highlightbackground=border,
        highlightcolor=border,
        width=138,
        height=108,
    )
    cell.grid(row=row, column=column, sticky="nsew", padx=3, pady=3)
    cell.grid_propagate(False)

    header = tk.Frame(cell, bg=bg)
    header.pack(fill="x", padx=8, pady=(8, 4))

    if is_today:
        day_badge = tk.Label(
            header,
            text=str(day.day),
            bg=AGENDA_COLORS["accent"],
            fg=AGENDA_COLORS["header_text"],
            font=("Segoe UI Semibold", 10),
            width=3,
            pady=2,
        )
    else:
        day_badge = tk.Label(
            header,
            text=str(day.day),
            bg=bg,
            fg=AGENDA_COLORS["muted"] if not is_current_month else AGENDA_COLORS["text"],
            font=("Segoe UI Semibold", 10),
        )
    day_badge.pack(anchor="nw")

    if reservations:
        tk.Label(
            header,
            text=f"{len(reservations)}",
            bg=AGENDA_COLORS["green"] if is_current_month else AGENDA_COLORS["line"],
            fg=AGENDA_COLORS["header_text"] if is_current_month else AGENDA_COLORS["muted"],
            font=("Segoe UI Semibold", 8),
            padx=6,
            pady=1,
        ).pack(anchor="ne")

    body = tk.Frame(cell, bg=bg)
    body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    for reservation in reservations[:3]:
        add_reservation_chip(body, app, reservation)

    if len(reservations) > 3:
        tk.Label(
            body,
            text=f"+ {len(reservations) - 3} RESERVAS",
            bg=bg,
            fg=AGENDA_COLORS["muted"],
            font=("Segoe UI Semibold", 7),
        ).pack(anchor="w", pady=(2, 0))


def add_reservation_chip(parent, app, reservation):
    text = reservation_chip_text(reservation).upper()
    chip = tk.Button(
        parent,
        text=text,
        anchor="w",
        bg=AGENDA_COLORS["accent_soft"],
        fg=AGENDA_COLORS["accent"],
        activebackground=COLORS["primary_soft"],
        activeforeground=COLORS["primary_dark"],
        bd=0,
        relief="flat",
        font=("Segoe UI Semibold", 8),
        padx=8,
        pady=4,
        cursor="hand2",
        command=lambda: open_reservation_details(app, reservation),
    )
    chip.pack(fill="x", pady=(0, 4))


def reservation_chip_text(reservation):
    number = reservation.get("numero", "")
    kind = reservation.get("tipo", "Transfer")
    client = reservation.get("cliente", "")
    hour = reservation.get("hora") or extract_hour(reservation.get("data", ""))
    if kind == "Ida" or "Somente Ida" in kind:
        short_kind = "IDA"
    elif kind == "Volta":
        short_kind = "VOLTA"
    else:
        short_kind = kind[:6].upper()
    suffix = f" - {hour}" if hour else ""
    return f"{number}  {short_kind}  {client[:18]}{suffix}"


def extract_hour(value):
    if not value or " " not in value:
        return ""
    return value.split(" ", 1)[1][:5]


def group_reservations_by_day(reservations):
    grouped = {}
    for reservation in reservations:
        reservation_date = parse_reservation_date(reservation)
        if not reservation_date:
            continue
        grouped.setdefault(reservation_date, []).append(reservation)
    return grouped


def parse_reservation_date(reservation):
    if isinstance(reservation, str):
        value = reservation
    else:
        value = reservation.get("data", "")
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def change_agenda_month(app, delta):
    current = app.agenda_month
    month_index = current.month + delta
    year = current.year
    if month_index < 1:
        month_index = 12
        year -= 1
    elif month_index > 12:
        month_index = 1
        year += 1
    app.agenda_month = date(year, month_index, 1)
    app.show_page("AGENDA")


def go_to_today(app):
    app.agenda_month = date.today().replace(day=1)
    app.show_page("AGENDA")


def agenda_button(parent, text, command, width=None, style="secondary"):
    return styled_button(parent, text, style=style, size="sm", width=width, command=command)


def open_reservation_details(app, reservation):
    window = tk.Toplevel(app)
    window.title(f"Detalhes da Reserva {reservation.get('numero', '')}")
    window.geometry("460x620")
    window.minsize(420, 520)
    window.configure(bg=AGENDA_COLORS["bg"])
    window.transient(app)
    window.grab_set()

    shell = tk.Frame(window, bg=AGENDA_COLORS["panel"])
    shell.pack(fill="both", expand=True, padx=12, pady=12)

    top = tk.Frame(shell, bg=AGENDA_COLORS["panel"])
    top.pack(fill="x", padx=14, pady=(14, 8))
    tk.Label(top, text="Detalhes da Reserva", bg=AGENDA_COLORS["panel"], fg=AGENDA_COLORS["text"], font=("Segoe UI Semibold", 14)).pack(anchor="w")
    tk.Label(top, text=f"Reserva {reservation.get('numero', '-')}", bg=AGENDA_COLORS["panel"], fg=AGENDA_COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))

    canvas = tk.Canvas(shell, bg=AGENDA_COLORS["panel"], highlightthickness=0)
    scrollbar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview)
    body = tk.Frame(canvas, bg=AGENDA_COLORS["panel"])
    body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(canvas_window, width=event.width))
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=(0, 14))
    scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=(0, 14))

    detail_section(
        body,
        "Informacoes do Cliente",
        [
            ("Cliente", reservation.get("cliente", "-")),
            ("CPF/CNPJ", reservation.get("documento", "-")),
            ("Telefone", reservation.get("contato", "-")),
            ("Email", reservation.get("email", "-")),
            ("Quem Viaja", reservation.get("quem_faz", "Motorista")),
        ],
    )
    detail_section(
        body,
        "Detalhes da Viagem",
        [
            ("Tipo de Viagem", reservation.get("tipo", "-")),
            ("Status", reservation.get("status", "-")),
            ("Data", reservation.get("data", "-")),
            ("Hora", reservation.get("hora", "-")),
            ("Motorista", reservation.get("motorista", "-")),
            ("Passageiros", reservation.get("passageiros", "-")),
            ("Trajeto", reservation.get("trajeto", "-")),
        ],
    )
    detail_section(
        body,
        "Valores e Pagamento",
        [
            ("Valor", reservation.get("valor", reservation.get("valor_base", "-"))),
            ("Desconto", reservation.get("desconto", "-")),
            ("Metodo de Pagamento", reservation.get("pagamento", "-")),
            ("Repasse ao motorista", reservation.get("repasse", "-")),
        ],
    )
    detail_section(body, "Observacoes", [("Observacoes", reservation.get("observacoes", "-"))])


def detail_section(parent, title, rows):
    box = tk.Frame(parent, bg=AGENDA_COLORS["panel"], highlightthickness=1, highlightbackground=AGENDA_COLORS["line"])
    box.pack(fill="x", pady=(0, 12))
    tk.Label(box, text=title, bg=AGENDA_COLORS["panel"], fg=AGENDA_COLORS["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=10, pady=(10, 7))

    for label, value in rows:
        line = tk.Frame(box, bg=AGENDA_COLORS["panel"])
        line.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(line, text=label, bg=AGENDA_COLORS["panel"], fg=AGENDA_COLORS["muted"], font=("Segoe UI Semibold", 8), width=18, anchor="w").pack(side="left")
        tk.Label(line, text=value or "-", bg=AGENDA_COLORS["panel"], fg=AGENDA_COLORS["text"], font=("Segoe UI", 9), anchor="w", justify="left", wraplength=230).pack(side="left", fill="x", expand=True)


def render_metricas(parent, app):
    parent.configure(bg=COLORS["bg"])
    reservations = _metrics_reservations(app)
    stats = build_metrics_stats(reservations)

    _, body = table_scroll_host(parent)

    header = tk.Frame(body, bg=COLORS["panel"])
    header.pack(fill="x", pady=(0, 12))
    title_box = tk.Frame(header, bg=COLORS["panel"])
    title_box.pack(side="left", fill="x", expand=True, padx=14, pady=12)
    tk.Label(title_box, text="METRICAS E PERFORMANCE", bg=COLORS["panel"], fg=COLORS["primary"], font=("Segoe UI Semibold", 18)).pack(anchor="w")
    tk.Label(
        title_box,
        text="Indicadores de performance, receita, reservas e operacao. Dados carregados da base de reservas.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
        wraplength=760,
        justify="left",
    ).pack(anchor="w", pady=(2, 0))
    styled_button(header, "Atualizar", style="secondary", command=lambda: app.show_page("METRICAS")).pack(side="right", padx=14, pady=12)

    cards = tk.Frame(body, bg=COLORS["bg"])
    cards.pack(fill="x", pady=(0, 12))
    card_data = [
        ("Reservas", str(stats["total"]), "total na base", COLORS["primary"]),
        ("Receita", money_display(stats["revenue"]), "valor total", COLORS["success"]),
        ("Ticket medio", money_display(stats["ticket"]), "por reserva", COLORS["warning"]),
        ("Concluidas", str(stats["done"]), f"{stats['done_pct']}% do total", COLORS["success"]),
        ("Pendentes", str(stats["pending"]), "requer acompanhamento", COLORS["danger"]),
    ]
    for index, item in enumerate(card_data):
        cards.grid_columnconfigure(index, weight=1, uniform="metric_cards")
        metric_card(cards, *item).grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 5, 0 if index == len(card_data) - 1 else 5))

    middle = tk.Frame(body, bg=COLORS["bg"], height=260)
    middle.pack(fill="x", pady=(0, 12))
    middle.pack_propagate(False)
    middle.grid_columnconfigure(0, weight=3)
    middle.grid_columnconfigure(1, weight=2)
    middle.grid_rowconfigure(0, weight=1)

    evolution = panel_card(middle, "Evolucao mensal", "Reservas e receita por mes")
    evolution.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    draw_line_chart(evolution.body, stats["monthly"])

    channels = panel_card(middle, "Status das reservas", "Distribuicao operacional")
    channels.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    draw_status_bars(channels.body, stats["statuses"])

    bottom = tk.Frame(body, bg=COLORS["bg"], height=240)
    bottom.pack(fill="x", pady=(0, 12))
    bottom.pack_propagate(False)
    bottom.grid_columnconfigure(0, weight=1)
    bottom.grid_columnconfigure(1, weight=1)
    bottom.grid_rowconfigure(0, weight=1)

    latest = panel_card(bottom, "Ultimos Transfers", f"{min(len(reservations), 5)} recentes")
    latest.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    render_latest_reservations(latest.body, reservations[:5])

    ranking = panel_card(bottom, "Top destinos", "principais trajetos")
    ranking.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    render_top_routes(ranking.body, stats["routes"])

def _metrics_reservations(app):
    items = getattr(app, "reservations", []) or []
    return [item for item in items if isinstance(item, dict)]


def build_metrics_stats(reservations):
    reservations = [item for item in reservations if isinstance(item, dict)]
    total = len(reservations)
    revenue = sum(parse_money_value(item.get("valor", "")) for item in reservations)
    done = count_by_status(reservations, "Concluida")
    pending = count_by_status(reservations, "Pendente")
    ticket = revenue / total if total else 0
    monthly = monthly_summary(reservations)
    statuses = {
        "Pendentes": pending,
        "Confirmadas": count_by_status(reservations, "Confirmada"),
        "Concluidas": done,
        "Canceladas": count_by_status(reservations, "Cancelada"),
    }
    return {
        "total": total,
        "revenue": revenue,
        "ticket": ticket,
        "done": done,
        "done_pct": int((done / total) * 100) if total else 0,
        "pending": pending,
        "monthly": monthly,
        "statuses": statuses,
        "routes": top_routes(reservations),
    }


def metric_card(parent, title, value, subtitle, color):
    card = panel_frame(parent)
    tk.Frame(card, bg=color, height=3).pack(fill="x")
    tk.Label(card, text=title, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=14, pady=(12, 2))
    tk.Label(card, text=value, bg=COLORS["panel"], fg=color, font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=14)
    tk.Label(card, text=subtitle, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=14, pady=(0, 12))
    return card


def panel_card(parent, title, subtitle):
    panel = panel_frame(parent)
    header = tk.Frame(panel, bg=COLORS["panel_alt"])
    header.pack(fill="x")
    tk.Label(header, text=title, bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(side="left", padx=14, pady=10)
    tk.Label(header, text=subtitle, bg=COLORS["panel_alt"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(side="right", padx=14, pady=10)
    body = tk.Frame(panel, bg=COLORS["panel"])
    body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
    panel.body = body
    return panel


def draw_line_chart(parent, monthly):
    canvas = tk.Canvas(parent, height=170, bg=COLORS["panel"], highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    width = 520
    height = 150
    left = 34
    bottom = 125
    max_value = max([item["count"] for item in monthly] + [1])

    for step in range(4):
        y = bottom - step * 30
        canvas.create_line(left, y, width, y, fill="#D8E0EA")
        canvas.create_text(8, y, text=str(step), anchor="w", fill=COLORS["muted"], font=("Segoe UI", 7))

    points = []
    gap = (width - left - 18) / max(len(monthly) - 1, 1)
    for index, item in enumerate(monthly):
        x = left + index * gap
        y = bottom - (item["count"] / max_value) * 92
        points.append((x, y))
        canvas.create_rectangle(x - 7, bottom, x + 7, y, fill="#CFE0F5", outline="#9EB9D9")
        canvas.create_text(x, 142, text=item["label"], fill=COLORS["muted"], font=("Segoe UI", 7))

    for start, end in zip(points, points[1:]):
        canvas.create_line(start[0], start[1], end[0], end[1], fill=COLORS["warning"], width=2)
    for x, y in points:
        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=COLORS["warning"], outline=COLORS["warning"])


def draw_status_bars(parent, statuses):
    total = max(sum(statuses.values()), 1)
    colors = {
        "Pendentes": COLORS["warning"],
        "Confirmadas": COLORS["primary"],
        "Concluidas": COLORS["success"],
        "Canceladas": COLORS["danger"],
    }
    for label, value in statuses.items():
        row = tk.Frame(parent, bg=COLORS["panel"])
        row.pack(fill="x", pady=6)
        tk.Label(row, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9), width=12, anchor="w").pack(side="left")
        bar_box = tk.Frame(row, bg="#E5EAF1", height=14)
        bar_box.pack(side="left", fill="x", expand=True, padx=8)
        bar_box.pack_propagate(False)
        tk.Frame(bar_box, bg=colors[label], width=max(int((value / total) * 220), 8), height=14).pack(side="left")
        tk.Label(row, text=str(value), bg=COLORS["panel"], fg=COLORS["muted"], font=("Consolas", 9, "bold"), width=4).pack(side="right")


def render_latest_reservations(parent, reservations):
    if not reservations:
        tk.Label(parent, text="Nenhuma reserva encontrada.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=8)
        return
    for reservation in reservations:
        line = tk.Frame(parent, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground="#D8E0EA")
        line.pack(fill="x", pady=(0, 7))
        left = tk.Frame(line, bg=COLORS["panel_alt"])
        left.pack(side="left", fill="x", expand=True, padx=10, pady=7)
        tk.Label(left, text=f'{reservation.get("numero", "")} - {reservation.get("cliente", "")}', bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
        tk.Label(left, text=reservation.get("trajeto", ""), bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 8), wraplength=420, justify="left").pack(anchor="w")
        right = tk.Frame(line, bg=COLORS["panel_alt"])
        right.pack(side="right", padx=10)
        tk.Label(right, text=reservation.get("valor", "R$ 0,00"), bg=COLORS["panel_alt"], fg=COLORS["primary"], font=("Segoe UI Semibold", 9)).pack(anchor="e")
        tk.Label(right, text=reservation.get("status", ""), bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="e")


def render_top_routes(parent, routes):
    if not routes:
        tk.Label(parent, text="Sem trajetos para exibir.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=8)
        return
    max_count = max(count for _, count in routes)
    for index, (route, count) in enumerate(routes, start=1):
        tk.Label(parent, text=f"{index}. {route[:58]}", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="w", pady=(4, 2))
        bar = tk.Frame(parent, bg="#E5EAF1", height=10)
        bar.pack(fill="x", pady=(0, 7))
        bar.pack_propagate(False)
        tk.Frame(bar, bg=COLORS["warning"], width=max(int((count / max_count) * 420), 18), height=10).pack(side="left")


def monthly_summary(reservations):
    today = date.today()
    months = []
    for offset in range(5, -1, -1):
        month = today.month - offset
        year = today.year
        while month < 1:
            month += 12
            year -= 1
        months.append({"month": month, "year": year, "label": MONTH_NAMES[month][:3], "count": 0, "revenue": 0})

    for reservation in reservations:
        reservation_date = parse_reservation_date(reservation)
        if not reservation_date:
            continue
        for item in months:
            if item["month"] == reservation_date.month and item["year"] == reservation_date.year:
                item["count"] += 1
                item["revenue"] += parse_money_value(reservation.get("valor", ""))
    return months


def top_routes(reservations):
    counts = {}
    for reservation in reservations:
        route = reservation.get("trajeto") or "Sem trajeto"
        counts[route] = counts.get(route, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]


def count_by_status(reservations, status):
    return sum(1 for item in reservations if item.get("status") == status)


def parse_money_value(value):
    text = str(value or "0").replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(text)
    except ValueError:
        return 0


def money_display(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")



def render_finance(parent, app, key):
    parent.configure(bg=COLORS["bg"])
    reservations = getattr(app, "reservations", [])
    summary = build_finance_summary(reservations)

    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", padx=2, pady=(2, 12))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    titles = {
        "FIN_DASHBOARD": ("Financeiro", "Visao geral de receitas, repasses, recebiveis e resultado operacional."),
        "FIN_LANCAMENTOS": ("Lancamentos", "Entradas e saidas geradas automaticamente pelas reservas de transfer."),
        "FIN_CONTAS_PAGAR": ("Contas a pagar", "Repasses e compromissos previstos com motoristas."),
        "FIN_CONTAS_RECEBER": ("Contas a receber", "Valores previstos para recebimento dos clientes."),
        "FIN_RELATORIOS": ("Relatorios financeiros", "Fechamento, margens e leituras para conferencia."),
    }
    title, subtitle = titles[key]
    tk.Label(title_box, text=title, bg=COLORS["bg"], fg=COLORS["primary"], font=("Segoe UI Semibold", 18)).pack(anchor="w")
    tk.Label(title_box, text=subtitle, bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
    styled_button(header, "Atualizar", style="secondary", command=app.refresh_reservations).pack(side="right", anchor="n")

    if key == "FIN_DASHBOARD":
        render_finance_dashboard(parent, summary)
    elif key == "FIN_LANCAMENTOS":
        render_finance_entries(parent, summary["entries"])
    elif key == "FIN_CONTAS_PAGAR":
        render_finance_payables(parent, summary["payables"])
    elif key == "FIN_CONTAS_RECEBER":
        render_finance_receivables(parent, summary["receivables"])
    elif key == "FIN_RELATORIOS":
        render_finance_reports(parent, summary)


def render_finance_dashboard(parent, summary):
    cards = tk.Frame(parent, bg=COLORS["bg"])
    cards.pack(fill="x", padx=2, pady=(0, 12))
    card_data = [
        ("Receita prevista", money_display(summary["gross_revenue"]), "reservas nao canceladas", COLORS["primary"]),
        ("Recebido", money_display(summary["received"]), "reservas concluidas", COLORS["success"]),
        ("A receber", money_display(summary["to_receive"]), "pendente/confirmado", COLORS["warning"]),
        ("A pagar", money_display(summary["to_pay"]), "repasses motoristas", COLORS["danger"]),
        ("Resultado", money_display(summary["net_result"]), "receita - repasses", COLORS["success"] if summary["net_result"] >= 0 else COLORS["danger"]),
    ]
    for index, item in enumerate(card_data):
        cards.grid_columnconfigure(index, weight=1, uniform="finance_cards")
        metric_card(cards, *item).grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 5, 0 if index == len(card_data) - 1 else 5))

    content = tk.Frame(parent, bg=COLORS["bg"])
    content.pack(fill="both", expand=True, padx=2)
    content.grid_columnconfigure(0, weight=3, uniform="finance")
    content.grid_columnconfigure(1, weight=2, uniform="finance")
    content.grid_rowconfigure(0, weight=1)

    flow = panel_card(content, "Fluxo financeiro", "entradas x saidas")
    flow.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    draw_finance_bars(flow.body, summary)

    status = panel_card(content, "Saude da operacao", "indicadores de controle")
    status.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    render_finance_health(status.body, summary)


def render_finance_entries(parent, entries):
    table = panel_card(parent, "Lancamentos contabilizados", f"{len(entries)} movimentos")
    table.pack(fill="both", expand=True, padx=2)
    simple_table(
        table.body,
        ["Data", "Tipo", "Descricao", "Categoria", "Valor", "Status"],
        [
            (
                entry["date"],
                entry["type"],
                entry["description"],
                entry["category"],
                money_display(entry["value"]),
                entry["status"],
            )
            for entry in entries
        ],
    )


def render_finance_payables(parent, payables):
    table = panel_card(parent, "Contas a pagar", f"{len(payables)} repasses previstos")
    table.pack(fill="both", expand=True, padx=2)
    simple_table(
        table.body,
        ["Vencimento", "Conta", "Motorista", "Reserva", "Descricao", "Valor", "Status"],
        [
            (
                item["date"],
                item.get("account", "CP-REPASSE"),
                item["driver"],
                item["number"],
                item["description"],
                money_display(item["value"]),
                item["status"],
            )
            for item in payables
        ],
    )


def render_finance_receivables(parent, receivables):
    table = panel_card(parent, "Contas a receber", f"{len(receivables)} receitas previstas")
    table.pack(fill="both", expand=True, padx=2)
    simple_table(
        table.body,
        ["Previsao", "Cliente", "Reserva", "Trajeto", "Valor", "Status"],
        [
            (
                item["date"],
                item["client"],
                item["number"],
                item["route"],
                money_display(item["value"]),
                item["status"],
            )
            for item in receivables
        ],
    )


def render_finance_reports(parent, summary):
    cards = tk.Frame(parent, bg=COLORS["bg"])
    cards.pack(fill="x", padx=2, pady=(0, 12))
    reports = [
        ("Margem operacional", f"{summary['margin_pct']}%", "sobre receita prevista", COLORS["success"] if summary["margin_pct"] >= 0 else COLORS["danger"]),
        ("Reservas contabilizadas", str(summary["reservation_count"]), "base financeira", COLORS["primary"]),
        ("Ticket medio", money_display(summary["average_ticket"]), "valor medio por transfer", COLORS["warning"]),
        ("Repasses", money_display(summary["total_repasse"]), "custo motorista", COLORS["danger"]),
    ]
    for index, item in enumerate(reports):
        cards.grid_columnconfigure(index, weight=1, uniform="finance_reports")
        metric_card(cards, *item).grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 5, 0 if index == len(reports) - 1 else 5))

    content = tk.Frame(parent, bg=COLORS["bg"])
    content.pack(fill="both", expand=True, padx=2)
    content.grid_columnconfigure(0, weight=1, uniform="reports")
    content.grid_columnconfigure(1, weight=1, uniform="reports")

    summary_panel = panel_card(content, "Resumo por status", "controle financeiro")
    summary_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    draw_status_bars(summary_panel.body, summary["status_counts"])

    closing_panel = panel_card(content, "Fechamento sugerido", "rotina para conferencia")
    closing_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    checklist = [
        "Conferir reservas concluidas antes de marcar receita como recebida.",
        "Validar repasse do motorista antes de baixar contas a pagar.",
        "Comparar valor base, desconto e valor total de cada reserva.",
        "Exportar relatorio mensal apos conciliacao dos lancamentos.",
    ]
    for item in checklist:
        tk.Label(closing_panel.body, text=f"- {item}", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI", 9), wraplength=430, justify="left").pack(anchor="w", pady=5)


def build_finance_summary(reservations):
    active = [item for item in reservations if item.get("status") != "Cancelada"]
    entries = []
    payables = []
    receivables = []

    for reservation in active:
        value = parse_money_value(reservation.get("valor"))
        repasse = parse_money_value(reservation.get("repasse"))
        status = reservation.get("status") or "Pendente"
        received = status == "Concluida"
        number = reservation.get("numero", "")
        date_label = reservation.get("data") or "-"

        entries.append(
            {
                "date": date_label,
                "type": "Entrada",
                "description": f"Receita transfer {number} - {reservation.get('cliente', '')}",
                "category": "Receita de transfer",
                "value": value,
                "status": "Recebido" if received else "Previsto",
            }
        )
        if not received:
            receivables.append(
                {
                    "date": date_label,
                    "client": reservation.get("cliente", ""),
                    "number": number,
                    "route": reservation.get("trajeto", ""),
                    "value": value,
                    "status": status,
                }
            )
        if repasse > 0:
            account = reservation.get("conta_pagar") or f"CP-REPASSE-{str(number).replace('#', '')}"
            account_label = reservation.get("conta_pagar_descricao") or f"Repasse motorista — {reservation.get('motorista', '-')}"
            entries.append(
                {
                    "date": date_label,
                    "type": "Saida",
                    "description": f"{account} — {account_label}",
                    "category": "Repasse motorista",
                    "value": repasse,
                    "status": "Pago" if received else "A pagar",
                }
            )
            payables.append(
                {
                    "date": date_label,
                    "driver": reservation.get("motorista", "-"),
                    "number": number,
                    "account": account,
                    "description": account_label,
                    "value": repasse,
                    "status": "Pago" if received else "A pagar",
                }
            )

    gross_revenue = sum(parse_money_value(item.get("valor")) for item in active)
    received = sum(parse_money_value(item.get("valor")) for item in active if item.get("status") == "Concluida")
    total_repasse = sum(parse_money_value(item.get("repasse")) for item in active)
    to_pay = sum(item["value"] for item in payables if item["status"] == "A pagar")
    to_receive = sum(item["value"] for item in receivables)
    net_result = gross_revenue - total_repasse
    count = len(active)

    return {
        "reservation_count": count,
        "gross_revenue": gross_revenue,
        "received": received,
        "to_receive": to_receive,
        "to_pay": to_pay,
        "total_repasse": total_repasse,
        "net_result": net_result,
        "average_ticket": gross_revenue / count if count else 0,
        "margin_pct": round((net_result / gross_revenue) * 100, 1) if gross_revenue else 0,
        "entries": entries,
        "payables": payables,
        "receivables": receivables,
        "status_counts": {
            "Pendentes": count_by_status(active, "Pendente"),
            "Confirmadas": count_by_status(active, "Confirmada"),
            "Concluidas": count_by_status(active, "Concluida"),
            "Canceladas": count_by_status(reservations, "Cancelada"),
        },
    }


def draw_finance_bars(parent, summary):
    items = [
        ("Receita prevista", summary["gross_revenue"], COLORS["primary"]),
        ("Recebido", summary["received"], COLORS["success"]),
        ("A receber", summary["to_receive"], COLORS["warning"]),
        ("A pagar", summary["to_pay"], COLORS["danger"]),
        ("Resultado", summary["net_result"], COLORS["accent"]),
    ]
    max_value = max([abs(value) for _, value, _ in items] + [1])
    for label, value, color in items:
        row = tk.Frame(parent, bg=COLORS["panel"])
        row.pack(fill="x", pady=7)
        tk.Label(row, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9), width=16, anchor="w").pack(side="left")
        bar_box = tk.Frame(row, bg="#E5EAF1", height=16)
        bar_box.pack(side="left", fill="x", expand=True, padx=8)
        bar_box.pack_propagate(False)
        tk.Frame(bar_box, bg=color, width=max(int((abs(value) / max_value) * 280), 10), height=16).pack(side="left")
        tk.Label(row, text=money_display(value), bg=COLORS["panel"], fg=color, font=("Consolas", 9, "bold"), width=13, anchor="e").pack(side="right")


def render_finance_health(parent, summary):
    items = [
        ("Margem", f"{summary['margin_pct']}%", COLORS["success"] if summary["margin_pct"] >= 0 else COLORS["danger"]),
        ("Ticket medio", money_display(summary["average_ticket"]), COLORS["primary"]),
        ("Lancamentos", str(len(summary["entries"])), COLORS["warning"]),
        ("Pendencias", str(len(summary["payables"]) + len(summary["receivables"])), COLORS["danger"]),
    ]
    for label, value, color in items:
        line = tk.Frame(parent, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground="#D8E0EA")
        line.pack(fill="x", pady=(0, 8))
        tk.Label(line, text=label, bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=10, pady=(7, 1))
        tk.Label(line, text=value, bg=COLORS["panel_alt"], fg=color, font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=10, pady=(0, 7))


def simple_table(parent, columns, rows):
    table = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    table.pack(fill="both", expand=True)
    for column, title in enumerate(columns):
        table.grid_columnconfigure(column, weight=1, uniform="finance_table")
        tk.Label(
            table,
            text=title,
            bg="#D9E2EE",
            fg=COLORS["text"],
            font=("Segoe UI Semibold", 8),
            anchor="w",
            padx=8,
            pady=7,
        ).grid(row=0, column=column, sticky="ew")

    if not rows:
        tk.Label(table, text="Nenhum registro encontrado.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9), pady=20).grid(row=1, column=0, columnspan=len(columns), sticky="ew")
        return

    for row_index, row in enumerate(rows, start=1):
        bg = COLORS["panel"] if row_index % 2 else COLORS["panel_alt"]
        for column, value in enumerate(row):
            tk.Label(
                table,
                text=value,
                bg=bg,
                fg=COLORS["text"],
                font=("Segoe UI", 8),
                anchor="w",
                justify="left",
                padx=8,
                pady=7,
                wraplength=190,
            ).grid(row=row_index, column=column, sticky="nsew")



def render_transfer(parent, key):
    app = parent.winfo_toplevel()
    if key == "SOLICITACOES":
        render_solicitacoes(parent, app)
        return
    page_data = TRANSFER_PAGES[key]
    title, subtitle, action = page_data["header"]
    header_panel(parent, title, subtitle, action)
    summary_cards(parent, page_data["cards"])
    data_table(parent, TRANSFER_COLUMNS, page_data["rows"])


def render_solicitacoes(parent, app):
    from .platform import ensure_platform_collections

    parent.configure(bg=COLORS["bg"])
    ensure_platform_collections(app)
    requests = [item for item in getattr(app, "transport_requests", []) if isinstance(item, dict)]

    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 10))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Solicitacoes de Transfer", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI Semibold", 18)).pack(anchor="w")
    tk.Label(
        title_box,
        text="Pedidos reais recebidos via portal, webhooks e cadastros. Sem dados ficticios.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
    ).pack(anchor="w", pady=(2, 0))
    styled_button(header, "Atualizar", style="secondary", command=lambda: app.show_page("SOLICITACOES")).pack(side="right")

    pending = sum(1 for item in requests if item.get("status") in {"Recebida", "Em analise"})
    quoted = sum(1 for item in requests if item.get("status") == "Cotada")
    confirmed = sum(1 for item in requests if item.get("status") == "Confirmada")
    cancelled = sum(1 for item in requests if item.get("status") == "Cancelada")

    cards = tk.Frame(parent, bg=COLORS["bg"])
    cards.pack(fill="x", pady=(0, 10))
    summary_cards(
        cards,
        [
            {"label": "Aguardando analise", "value": str(pending), "hint": "Recebidas + em analise"},
            {"label": "Em cotacao", "value": str(quoted), "hint": "Aguardando precificacao"},
            {"label": "Confirmadas", "value": str(confirmed), "hint": "Prontas para reserva"},
            {"label": "Canceladas", "value": str(cancelled), "hint": "Encerradas", "tone": "danger"},
        ],
    )

    if not requests:
        box = panel_frame(parent)
        box.pack(fill="both", expand=True)
        tk.Label(
            box,
            text="Nenhuma solicitacao registrada ainda.\nUse webhooks em Automacoes ou o portal da empresa.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            justify="center",
        ).pack(pady=60)
        return

    _, table = table_scroll_host(parent)
    weights = [1, 2, 2, 2, 1, 0]
    minsizes = [0, 0, 0, 0, 0, 300]
    headers = ["Codigo", "Cliente", "Data/Hora", "Trajeto", "Status", "Acoes"]
    grid_table_header(table, headers, weights, minsizes)

    for row_index, request in enumerate(requests, start=1):
        bg = COLORS["panel"] if row_index % 2 else COLORS["panel_alt"]
        trajeto = f'{request.get("origem", "-")} -> {request.get("destino", "-")}'
        cliente = request.get("nome") or request.get("empresa") or "-"
        when = " ".join(part for part in [request.get("data", ""), request.get("hora", "")] if part).strip() or "-"
        values = [request.get("id", ""), cliente, when, trajeto, request.get("status", "")]
        trunc = [None, 24, 16, 40, None]
        for col, value in enumerate(values):
            grid_table_cell(table, row_index, col, value, bg, truncate=trunc[col])

        actions = tk.Frame(table, bg=bg)
        actions.grid(row=row_index, column=5, sticky="ew", padx=4, pady=4)
        render_action_buttons(
            actions,
            [
                ("Ver", lambda req=request: show_solicitacao_details(app, req)),
                ("Confirmar", lambda req=request: update_solicitacao_status(app, req, "Confirmada"), "success"),
                ("Excluir", lambda req=request: delete_solicitacao(app, req)),
            ],
            bg=bg,
        )


def show_solicitacao_details(app, request):
    lines = [
        f"ID: {request.get('id', '')}",
        f"Cliente: {request.get('nome') or request.get('empresa', '')}",
        f"Telefone: {request.get('telefone', '')}",
        f"E-mail: {request.get('email', '')}",
        f"Origem: {request.get('origem', '')}",
        f"Destino: {request.get('destino', '')}",
        f"Data: {request.get('data', '')} {request.get('hora', '')}".strip(),
        f"Status: {request.get('status', '')}",
        f"Observacoes: {request.get('observacoes', '-')}",
    ]
    messagebox.showinfo("Solicitacao", "\n".join(lines), parent=app)


def update_solicitacao_status(app, request, status):
    for index, item in enumerate(app.transport_requests):
        if item.get("id") == request.get("id"):
            app.transport_requests[index] = {**item, "status": status}
            break
    app.save_state()
    app.show_page("SOLICITACOES")


def delete_solicitacao(app, request):
    if not messagebox.askyesno("Excluir", f'Excluir solicitacao {request.get("id", "")}?', parent=app):
        return
    app.transport_requests = [item for item in app.transport_requests if item.get("id") != request.get("id")]
    app.save_state()
    app.show_page("SOLICITACOES")


def render_registry(parent, key):
    app = parent.winfo_toplevel()
    if key == "MOTORISTAS":
        render_drivers(parent, app)
        return
    if key == "VEICULOS":
        render_vehicles(parent, app)
        return
    render_standard_page(parent, REGISTRY_PAGES[key])


def render_drivers(parent, app):
    if not hasattr(app, "drivers"):
        app.drivers = []

    parent.configure(bg=COLORS["bg"])

    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))

    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Cadastro de motoristas", bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(
        title_box,
        text="Motoristas da frota, portal de acesso, contatos e acoes rapidas de operacao.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
    ).pack(anchor="w", pady=(2, 0))

    styled_button(header, "+ Novo motorista", style="success", size="lg", command=lambda: open_driver_form(app)).pack(side="right", anchor="n")

    search = tk.Frame(parent, bg=COLORS["bg"])
    search.pack(fill="x", pady=(0, 12))
    entry = tk.Entry(search, bg=COLORS["panel"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
    entry.pack(side="left", fill="x", expand=True, ipady=7)
    setup_placeholder(entry, "BUSCAR POR NOME OU CPF...")

    render_driver_table(parent, app)


def render_driver_table(parent, app):
    _, table = table_scroll_host(parent)
    weights = [3, 2, 2, 2, 1, 1, 1, 0]
    minsizes = [0, 0, 0, 0, 0, 0, 0, 380]
    headers = ["Nome", "CPF", "Telefone", "Cidade/UF", "Frota", "Portal", "Data", "Acoes"]
    grid_table_header(table, headers, weights, minsizes)

    for row_index, driver in enumerate(app.drivers, start=1):
        add_driver_row(table, app, driver, row_index)


def add_driver_row(table, app, driver, row_index):
    bg = COLORS["panel"] if row_index % 2 else COLORS["panel_alt"]
    values = [
        driver.get("nome", ""),
        driver.get("cpf", ""),
        driver.get("telefone", ""),
        driver.get("cidade", ""),
        driver.get("frota", "Ativo"),
        driver.get("portal", "Senha OK"),
        driver.get("data", ""),
    ]

    for col, value in enumerate(values):
        fg = COLORS["success"] if col == 4 and value == "Ativo" else COLORS["text"]
        font = ("Segoe UI Semibold", 9) if col == 4 else ("Segoe UI", 9)
        grid_table_cell(table, row_index, col, value, bg, fg=fg, font=font, truncate=24 if col == 0 else None)

    actions = tk.Frame(table, bg=bg)
    actions.grid(row=row_index, column=7, sticky="ew", padx=4, pady=5)
    render_action_buttons(
        actions,
        [
            ("Copiar link", lambda: copy_driver_link(app, driver)),
            ("Token portal", lambda: show_driver_activation_token(app, driver)),
            ("Detalhes", lambda: show_driver_details(app, driver)),
            ("Editar", lambda: open_driver_form(app, driver)),
        ],
        bg=bg,
    )


def copy_driver_link(app, driver):
    if not hasattr(app, "drivers"):
        app.drivers = []
    base_url = start_driver_portal_server(app)
    portal_link = f"{base_url}/driver/{driver_key(driver)}"
    driver["link"] = portal_link
    app.save_state()
    app.clipboard_clear()
    app.clipboard_append(portal_link)
    messagebox.showinfo("Copiar link", "Link do portal do motorista copiado.", parent=app)


def show_driver_activation_token(app, driver):
    token = generate_activation_token(driver)
    driver["portal_ativo"] = bool(driver.get("password_hash"))
    app.save_state()
    app.clipboard_clear()
    app.clipboard_append(token)
    status = "ativado" if driver_has_password(driver) else "pendente"
    messagebox.showinfo(
        "Token de ativacao",
        f"Token copiado para a area de transferencia.\n\n"
        f"Motorista: {driver.get('nome', '')} ({driver.get('id', '')})\n"
        f"Portal: {status}\n\n"
        f"Use POST /api/driver/set-password com slug, activation_token e password.",
        parent=app,
    )


def show_driver_details(app, driver):
    details = "\n".join(
        [
            f'Nome: {driver.get("nome", "")}',
            f'CPF: {driver.get("cpf", "")}',
            f'Telefone: {driver.get("telefone", "")}',
            f'Cidade/UF: {driver.get("cidade", "")}',
            f'Frota: {driver.get("frota", "")}',
            f'Portal: {driver.get("portal", "")}',
            f'Link: {driver.get("link", "")}',
        ]
    )
    messagebox.showinfo("Detalhes do motorista", details, parent=app)


def open_driver_form(app, driver=None):
    window = tk.Toplevel(app)
    editing = driver is not None
    window.title("Editar motorista" if editing else "Novo motorista")
    window.configure(bg=COLORS["bg"])
    window.geometry("860x720")
    window.minsize(780, 620)
    window.transient(app)
    window.grab_set()

    shell = tk.Frame(window, bg=COLORS["bg"])
    shell.pack(fill="both", expand=True, padx=12, pady=12)

    header = tk.Frame(shell, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    header.pack(fill="x", pady=(0, 10))
    tk.Label(header, text="Editar motorista" if editing else "Novo motorista", bg=COLORS["panel"], fg=COLORS["primary"], font=("Segoe UI Semibold", 16)).pack(anchor="w", padx=14, pady=(12, 2))
    tk.Label(
        header,
        text="Alteracoes aplicam-se apenas a este motorista na sua frota. A base de dados impede editar cadastros de outras contas.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
        wraplength=760,
        justify="left",
    ).pack(anchor="w", padx=14, pady=(0, 12))

    fields = {}

    tabs = tk.Frame(shell, bg=COLORS["bg"])
    tabs.pack(fill="x", pady=(0, 8))
    content = tk.Frame(shell, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    content.pack(fill="both", expand=True)
    footer = tk.Frame(shell, bg=COLORS["bg"])
    footer.pack(fill="x", pady=(10, 0))

    sections = {}
    tab_buttons = {}

    for step_key, label in [("pessoal", "Pessoal"), ("documentos", "Documentos"), ("pagamento", "Pagamento")]:
        tab_buttons[step_key] = tk.Button(
            tabs,
            text=label,
            bg=COLORS["panel"],
            fg=COLORS["primary"],
            activebackground="#E8EEF6",
            activeforeground=COLORS["primary_dark"],
            bd=1,
            relief="solid",
            padx=18,
            pady=7,
            cursor="hand2",
            font=("Segoe UI Semibold", 9),
            command=lambda key=step_key: show_driver_step(sections, tab_buttons, key),
        )
        tab_buttons[step_key].pack(side="left", padx=(0, 6))

        section_frame = tk.Frame(content, bg=COLORS["panel"])
        sections[step_key] = section_frame

    build_driver_personal_step(sections["pessoal"], fields, driver)
    build_driver_documents_step(sections["documentos"], fields, driver)
    build_driver_payment_step(sections["pagamento"], fields, driver)
    show_driver_step(sections, tab_buttons, "pessoal")

    tk.Button(footer, text="Cancelar", bg=COLORS["panel"], fg=COLORS["text"], bd=1, relief="solid", highlightbackground=COLORS["border"], padx=12, pady=7, cursor="hand2", font=FONTS["small"], command=window.destroy).pack(side="right")
    styled_button(
        footer,
        "Salvar",
        style="success",
        command=lambda: save_driver_form(app, window, fields, driver),
    ).pack(side="right", padx=(0, 8))


def show_driver_step(sections, tab_buttons, active_key):
    for key, frame in sections.items():
        frame.pack_forget()
        tab_buttons[key].configure(bg=COLORS["panel"], fg=COLORS["primary"])
    sections[active_key].pack(fill="both", expand=True, padx=14, pady=14)
    tab_buttons[active_key].configure(bg=COLORS["primary"], fg="white")


def build_driver_personal_step(parent, fields, driver):
    canvas = tk.Canvas(parent, bg=COLORS["panel"], highlightthickness=0)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    body = tk.Frame(canvas, bg=COLORS["panel"])
    body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(canvas_window, width=event.width - 6))
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    form_section_title(body, "Dados basicos")
    add_driver_input(body, fields, "nome", "Nome completo *", driver, example="motorista de exemplo")
    add_driver_input(body, fields, "cpf", "CPF *", driver, example="06436289917")
    add_driver_input(body, fields, "rg", "RG *", driver, example="102884353")
    add_driver_input(body, fields, "nascimento", "Data de nascimento *", driver, example="06/08/2002")
    add_driver_input(body, fields, "telefone", "Telefone *", driver, example="47988336609")
    add_driver_input(body, fields, "email", "E-mail *", driver, example="felipe.goulart06@hotmail.com")

    form_section_title(body, "Endereco (IBGE + ViaCEP)")
    add_driver_input(body, fields, "estado", "Estado (UF) *", driver, example="Santa Catarina (SC)")
    form_hint(body, "Fonte: API de localidades do IBGE.")
    add_driver_input(body, fields, "cidade_filtro", "Filtrar cidade *", driver, example="Digite ao menos 2 letras (ex.: cam)")
    add_driver_input(body, fields, "cidade", "Cidade (municipio IBGE) *", driver, example="")
    add_driver_input(body, fields, "cep", "CEP *", driver, example="88332490")
    form_hint(body, "ViaCEP preenche rua e bairro quando possivel.")
    add_driver_input(body, fields, "logradouro", "Logradouro (rua/avenida) *", driver, example="Rua Pedro pinto felipe")
    add_driver_input(body, fields, "numero", "Numero *", driver, example="87")
    add_driver_input(body, fields, "complemento", "Complemento", driver, example="casa")
    add_driver_input(body, fields, "bairro", "Bairro *", driver, example="Sao Judas Tadeu")

    form_section_title(body, "CNH")
    add_driver_input(body, fields, "cnh", "Numero da CNH *", driver, example="0000000000000")
    add_driver_input(body, fields, "categoria", "Categoria *", driver, example="B")
    add_driver_input(body, fields, "validade_cnh", "Validade *", driver, example="06/08/2030")
    add_driver_input(body, fields, "frota", "Situacao na frota *", driver, example="Ativo")
    form_hint(body, "Nao confundir com o estado do pre-cadastro na plataforma: aqui e so controle da sua frota.")
    add_driver_text(body, fields, "observacoes_motorista", "Observacoes (internas / solicitacao)", driver)


def build_driver_documents_step(parent, fields, driver):
    tk.Label(
        parent,
        text="Na edicao, os anexos sao opcionais. Envie novos ficheiros apenas para substituir documentos ja guardados (max. 5 MB cada; imagem ou PDF).",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
        wraplength=720,
        justify="left",
    ).pack(anchor="w", pady=(0, 14))

    for key, label in [
        ("foto_perfil", "Foto de perfil"),
        ("cnh_frente", "CNH - frente"),
        ("cnh_verso", "CNH - verso"),
        ("comprovante_residencia", "Comprovante de residencia"),
    ]:
        add_file_selector(parent, fields, key, label, driver)


def build_driver_payment_step(parent, fields, driver):
    form_section_title(parent, "Pagamento")
    add_driver_combo(parent, fields, "tipo_pagamento", "Como o motorista quer receber? *", driver, ["PIX", "Transferencia bancaria", "Dinheiro", "Outro"])
    add_driver_input(parent, fields, "pix_chave", "Chave PIX", driver, example="")
    add_driver_input(parent, fields, "banco", "Banco", driver, example="")
    add_driver_input(parent, fields, "agencia", "Agencia", driver, example="")
    add_driver_input(parent, fields, "conta", "Conta", driver, example="")
    add_driver_input(parent, fields, "titular", "Titular da conta", driver, example="")
    add_driver_input(parent, fields, "cpf_titular", "CPF/CNPJ do titular", driver, example="")
    add_driver_text(parent, fields, "observacoes_pagamento", "Observacoes de pagamento", driver)


def form_section_title(parent, text):
    tk.Label(parent, text=text, bg=COLORS["panel"], fg=COLORS["primary"], font=("Segoe UI Semibold", 11)).pack(anchor="w", pady=(8, 6))


def form_hint(parent, text):
    tk.Label(parent, text=text, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=2, pady=(0, 6))


def add_driver_input(parent, fields, key, label, driver, example=""):
    line = tk.Frame(parent, bg=COLORS["panel"])
    line.pack(fill="x", pady=4)
    tk.Label(line, text=label, bg=COLORS["panel"], fg=COLORS["muted"], width=28, anchor="w", font=("Segoe UI Semibold", 9)).pack(side="left")
    entry = tk.Entry(line, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
    entry.pack(side="left", fill="x", expand=True)
    raw = str(driver.get(key, "") or "").strip() if driver else ""
    apply_input_rules(entry, field_key=key, placeholder=example, label=label, value=raw)
    fields[key] = entry


def add_driver_combo(parent, fields, key, label, driver, values):
    line = tk.Frame(parent, bg=COLORS["panel"])
    line.pack(fill="x", pady=4)
    tk.Label(line, text=label, bg=COLORS["panel"], fg=COLORS["muted"], width=28, anchor="w", font=("Segoe UI Semibold", 9)).pack(side="left")
    combo = ttk.Combobox(line, values=values, state="readonly", font=("Segoe UI", 9))
    combo.pack(side="left", fill="x", expand=True)
    combo.set(driver.get(key, values[0]) if driver else values[0])
    fields[key] = combo


def add_driver_text(parent, fields, key, label, driver):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).pack(anchor="w", pady=(6, 3))
    text = tk.Text(parent, height=4, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9), wrap="word")
    text.pack(fill="x")
    text.insert("1.0", driver.get(key, "") if driver else "")
    fields[key] = text


def add_file_selector(parent, fields, key, label, driver):
    line = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground="#D3DAE3")
    line.pack(fill="x", pady=6)
    tk.Label(line, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(side="left", padx=10, pady=10)
    value = tk.StringVar(value=driver.get(key, "") if driver else "")
    fields[key] = value
    tk.Label(line, textvariable=value, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=8)
    styled_button(line, "Selecionar (max. 5MB)", style="outline_primary", size="sm", command=lambda: select_driver_file(value)).pack(side="right", padx=10)


def select_driver_file(value):
    filename = filedialog.askopenfilename(filetypes=[("Imagem ou PDF", "*.png *.jpg *.jpeg *.pdf"), ("Todos os arquivos", "*.*")])
    if filename:
        if os.path.getsize(filename) > 5 * 1024 * 1024:
            messagebox.showwarning("Arquivo muito grande", "Selecione um arquivo com no maximo 5 MB.")
            return
        value.set(filename)


def default_driver_value(key):
    defaults = {"frota": "Ativo", "portal": "Senha OK", "tipo_pagamento": "PIX"}
    return defaults.get(key, "")


def save_driver_form(app, window, fields, driver=None):
    values = {key: driver_field_value(field) for key, field in fields.items()}
    if not values["nome"]:
        messagebox.showwarning("Campo obrigatorio", "Informe o nome do motorista.", parent=window)
        return

    if driver is None:
        values["data"] = datetime.now().strftime("%d/%m/%Y")
        values = normalize_driver_record(values, app.drivers)
        values["link"] = f"{start_driver_portal_server(app)}/driver/{driver_key(values)}"
        app.drivers.insert(0, values)
    else:
        values = normalize_driver_record({**driver, **values}, app.drivers)
        driver.update(values)

    values["endereco_completo"] = ", ".join(
        part
        for part in [
            values.get("logradouro"),
            values.get("numero"),
            values.get("bairro"),
            values.get("cidade"),
            values.get("estado"),
            values.get("cep"),
        ]
        if str(part or "").strip()
    )

    app.save_state()
    window.destroy()
    app.show_page("MOTORISTAS")


def driver_field_value(field):
    if isinstance(field, tk.StringVar):
        return field.get().strip()
    if isinstance(field, ttk.Combobox):
        return field.get().strip()
    return resolve_widget_value(field)


def render_vehicles(parent, app):
    if not hasattr(app, "vehicles"):
        app.vehicles = []

    parent.configure(bg=COLORS["bg"])
    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))

    left = tk.Frame(header, bg=COLORS["bg"])
    left.pack(side="left", fill="x", expand=True)
    tk.Label(left, text="Veiculos", bg=COLORS["bg"], fg=COLORS["primary"], font=("Segoe UI Semibold", 18)).pack(anchor="w")
    tk.Label(left, text="Cadastro completo da frota para calculo automatico de corridas.", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w")

    styled_button(header, "+ Novo veiculo", style="success", size="lg", command=lambda: open_vehicle_form(app)).pack(side="right", anchor="n")

    cards = tk.Frame(parent, bg=COLORS["bg"])
    cards.pack(fill="x", pady=(0, 12))
    active_count = sum(1 for vehicle in app.vehicles if vehicle.get("status", "").lower() == "ativo")
    for index, (label, value, hint) in enumerate(
        [
            ("Total de veiculos", len(app.vehicles), "cadastrados"),
            ("Ativos", active_count, "disponiveis"),
            ("Com precificacao", len(app.vehicles), "taxas completas"),
            ("Vista", "Card ou tabela", "lista operacional"),
        ]
    ):
        cards.grid_columnconfigure(index, weight=1, uniform="vehicle_cards")
        card = tk.Frame(cards, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground="#D3DAE3")
        card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 5, 0 if index == 3 else 5))
        tk.Label(card, text=label, bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(9, 0))
        tk.Label(card, text=str(value), bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 14)).pack(anchor="w", padx=10)
        tk.Label(card, text=hint, bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(0, 9))

    search = tk.Entry(parent, bg=COLORS["panel"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
    search.pack(fill="x", ipady=7, pady=(0, 12))
    setup_placeholder(search, "BUSCAR POR PLACA, MARCA, MODELO OU TIPO...")

    render_vehicle_table(parent, app)


def render_vehicle_table(parent, app):
    _, table = table_scroll_host(parent)
    weights = [1, 3, 1, 1, 1, 2, 2, 0]
    minsizes = [0, 0, 0, 0, 0, 0, 0, 120]
    headers = ["Capa", "Marca / Modelo", "Placa", "Tipo", "Status", "KM / Hora", "Bandeirada / Min.", "Acoes"]
    grid_table_header(table, headers, weights, minsizes)

    for row, vehicle in enumerate(app.vehicles, start=1):
        add_vehicle_row(table, app, vehicle, row)


def add_vehicle_row(table, app, vehicle, row):
    bg = COLORS["panel"] if row % 2 else COLORS["panel_alt"]
    values = [
        "Imagem" if vehicle.get("capa") else "-",
        f'{vehicle.get("marca", "")} {vehicle.get("modelo", "")}',
        vehicle.get("placa", ""),
        vehicle.get("tipo_veiculo", ""),
        vehicle.get("status", ""),
        (
            f'R$ {vehicle.get("valor_km", "0")} / R$ {vehicle.get("valor_hora", "0")}'
            if is_network_vehicle(vehicle)
            else "Reserva manual"
        ),
        (
            f'R$ {vehicle.get("tarifa_base", "0")} / R$ {vehicle.get("valor_minimo", "0")}'
            if is_network_vehicle(vehicle)
            else "-"
        ),
    ]
    for column, value in enumerate(values):
        fg = COLORS["success"] if column == 4 else COLORS["text"]
        grid_table_cell(table, row, column, value, bg, fg=fg, truncate=22 if column == 1 else None)

    actions = tk.Frame(table, bg=bg)
    actions.grid(row=row, column=7, sticky="ew", padx=4, pady=5)
    render_action_buttons(actions, [("Editar", lambda: open_vehicle_form(app, vehicle))], bg=bg)


def open_vehicle_form(app, vehicle=None):
    window = tk.Toplevel(app)
    editing = vehicle is not None
    window.title("Editar veiculo" if editing else "Novo veiculo")
    window.configure(bg=COLORS["bg"])
    window.geometry("900x760")
    window.minsize(820, 640)
    window.transient(app)
    window.grab_set()

    shell = tk.Frame(window, bg=COLORS["bg"])
    shell.pack(fill="both", expand=True, padx=12, pady=12)

    header = tk.Frame(shell, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    header.pack(fill="x", pady=(0, 10))
    tk.Label(header, text="Novo veiculo" if not editing else "Editar veiculo", bg=COLORS["panel"], fg=COLORS["primary"], font=("Segoe UI Semibold", 16)).pack(anchor="w", padx=14, pady=(12, 2))
    tk.Label(
        header,
        text="Os dados do veiculo, imagens e taxas adicionais sao obrigatorios. A capa deve ter exatamente 1220x880 px e aparecera nos cards da lista.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
        wraplength=800,
        justify="left",
    ).pack(anchor="w", padx=14, pady=(0, 12))

    canvas = tk.Canvas(shell, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    scrollbar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview)
    form = tk.Frame(canvas, bg=COLORS["panel"])
    form.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas_window = canvas.create_window((0, 0), window=form, anchor="nw")
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(canvas_window, width=event.width - 6))
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")))
    canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

    fields = {}
    vehicle_section(form, "Dados do veiculo")
    add_vehicle_combo(form, fields, "tipo_veiculo", "Tipo de veiculo *", vehicle, list(VEHICLE_TYPES))
    add_vehicle_combo(form, fields, "status", "Status *", vehicle, ["Ativo", "Inativo", "Manutencao"])
    for key, label in [
        ("marca", "Marca *"),
        ("modelo", "Modelo *"),
        ("ano", "Ano *"),
        ("cor", "Cor *"),
        ("placa", "Placa *"),
    ]:
        add_vehicle_input(form, fields, key, label, vehicle)
    add_vehicle_combo(form, fields, "combustivel", "Combustivel *", vehicle, ["Gasolina", "Etanol", "Flex", "Diesel", "Eletrico", "Hibrido"])
    add_vehicle_input(form, fields, "renavam", "RENAVAM *", vehicle)
    add_vehicle_input(form, fields, "chassi", "Chassi *", vehicle)
    add_vehicle_file(form, fields, "capa", "Capa 1220x880 px *", vehicle)

    network_var = tk.BooleanVar(value=is_network_vehicle(vehicle))
    fields["veiculo_de_rede"] = network_var
    network_line = tk.Frame(form, bg=COLORS["panel"])
    network_line.pack(fill="x", padx=14, pady=(10, 4))
    tk.Checkbutton(
        network_line,
        text="VEICULO DE REDE?",
        variable=network_var,
        bg=COLORS["panel"],
        fg=COLORS["text"],
        activebackground=COLORS["panel"],
        activeforeground=COLORS["primary"],
        font=("Segoe UI Semibold", 10),
        anchor="w",
    ).pack(anchor="w")
    tk.Label(
        network_line,
        text="Se marcado, exibe Detalhes operacionais e calculo para o Motor de Reservas. Se nao, os valores sao definidos em Transfer > Reservas.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 8),
        wraplength=760,
        justify="left",
    ).pack(anchor="w", pady=(2, 0))

    operational_block = tk.Frame(form, bg=COLORS["panel"])
    operational_block.pack(fill="x")

    def _toggle_operational():
        if network_var.get():
            operational_block.pack(fill="x", after=network_line)
        else:
            operational_block.pack_forget()

    network_var.trace_add("write", lambda *_args: _toggle_operational())

    vehicle_section(operational_block, "Detalhes operacionais e calculo")
    for key, label in [
        ("valor_km", "Valor por KM *"),
        ("valor_hora", "Valor por hora *"),
        ("tarifa_base", "Tarifa base *"),
        ("valor_minimo", "Valor minimo *"),
        ("distancia_minima", "Distancia minima (KM) *"),
    ]:
        add_vehicle_input(operational_block, fields, key, label, vehicle)
    add_vehicle_combo(operational_block, fields, "tipo_cobranca", "Tipo de cobranca *", vehicle, ["Hibrido", "Por KM", "Por hora", "Preco fixo"])
    for key, label in [
        ("tolerancia_min", "Tolerancia (min) *"),
        ("valor_hora_espera", "Valor/hora espera *"),
        ("fracao_min", "Cobranca por fracao (min) *"),
        ("multiplicador_ida_volta", "Multiplicador ida e volta *"),
    ]:
        add_vehicle_input(operational_block, fields, key, label, vehicle)
    add_vehicle_combo(operational_block, fields, "preco_fixo_rota", "Permitir preco fixo por rota *", vehicle, ["Sim", "Nao"])

    vehicle_section(operational_block, "Taxas adicionais")
    add_vehicle_input(operational_block, fields, "taxa_noturna", "Taxa noturna (%) *", vehicle)
    add_vehicle_input(operational_block, fields, "taxa_aeroporto", "Taxa aeroporto (fixa) *", vehicle)
    add_vehicle_combo(operational_block, fields, "pedagio", "Pedagio *", vehicle, ["Sim", "Nao", "Conforme rota"])
    add_vehicle_text(operational_block, fields, "taxas_extras", "Taxas extras configuraveis *", vehicle, "Descreva todas as taxas extras aplicaveis.")

    _toggle_operational()

    vehicle_section(form, "Imagens do veiculo")
    for key, label in [
        ("img_dianteira", "Dianteira *"),
        ("img_traseira", "Traseira *"),
        ("img_lateral_esquerda", "Lateral esquerda *"),
        ("img_lateral_direita", "Lateral direita *"),
        ("img_externa_1", "Externa adicional 1 *"),
        ("img_externa_2", "Externa adicional 2 *"),
        ("img_externa_3", "Externa adicional 3 *"),
        ("img_externa_4", "Externa adicional 4 *"),
        ("img_interna_1", "Interna 1 *"),
        ("img_interna_2", "Interna 2 *"),
        ("img_interna_3", "Interna 3 *"),
        ("img_interna_4", "Interna 4 *"),
    ]:
        add_vehicle_file(form, fields, key, label, vehicle)

    add_vehicle_text(form, fields, "observacoes", "Observacoes do veiculo *", vehicle, "")

    footer = tk.Frame(form, bg=COLORS["panel"])
    footer.pack(fill="x", padx=14, pady=(14, 18))
    styled_button(footer, "Cancelar", style="secondary", command=window.destroy).pack(side="right")
    styled_button(footer, "Salvar veiculo", style="success", size="lg", command=lambda: save_vehicle_form(app, window, fields, vehicle)).pack(side="right", padx=(0, 8))


def vehicle_section(parent, title):
    tk.Label(parent, text=title, bg=COLORS["panel"], fg=COLORS["primary"], font=("Segoe UI Semibold", 11)).pack(anchor="w", padx=14, pady=(14, 6))


def add_vehicle_input(parent, fields, key, label, vehicle):
    line = tk.Frame(parent, bg=COLORS["panel"])
    line.pack(fill="x", padx=14, pady=4)
    tk.Label(line, text=label, bg=COLORS["panel"], fg=COLORS["muted"], width=30, anchor="w", font=("Segoe UI Semibold", 9)).pack(side="left")
    entry = tk.Entry(line, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
    entry.pack(side="left", fill="x", expand=True)
    entry.insert(0, vehicle.get(key, "") if vehicle else "")
    fields[key] = entry


def add_vehicle_combo(parent, fields, key, label, vehicle, values):
    line = tk.Frame(parent, bg=COLORS["panel"])
    line.pack(fill="x", padx=14, pady=4)
    tk.Label(line, text=label, bg=COLORS["panel"], fg=COLORS["muted"], width=30, anchor="w", font=("Segoe UI Semibold", 9)).pack(side="left")
    combo = ttk.Combobox(line, values=values, state="readonly", font=("Segoe UI", 9))
    combo.pack(side="left", fill="x", expand=True)
    combo.set(vehicle.get(key, values[0]) if vehicle else values[0])
    fields[key] = combo


def add_vehicle_file(parent, fields, key, label, vehicle):
    line = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground="#D3DAE3")
    line.pack(fill="x", padx=14, pady=5)
    tk.Label(line, text=label, bg=COLORS["panel"], fg=COLORS["text"], width=30, anchor="w", font=("Segoe UI Semibold", 9)).pack(side="left", padx=8, pady=8)
    value = tk.StringVar(value=vehicle.get(key, "") if vehicle else "")
    fields[key] = value
    tk.Label(line, textvariable=value, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=8)
    styled_button(line, "Selecionar imagem (max. 10MB)", style="outline_primary", size="sm", command=lambda: select_vehicle_image(value)).pack(side="right", padx=8)


def add_vehicle_text(parent, fields, key, label, vehicle, placeholder):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=14, pady=(7, 3))
    text = tk.Text(parent, height=4, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9), wrap="word")
    text.pack(fill="x", padx=14, pady=(0, 4))
    text.insert("1.0", vehicle.get(key, "") if vehicle else placeholder)
    fields[key] = text


def select_vehicle_image(value):
    filename = filedialog.askopenfilename(filetypes=[("Imagens", "*.png *.jpg *.jpeg"), ("Todos os arquivos", "*.*")])
    if not filename:
        return
    if os.path.getsize(filename) > 10 * 1024 * 1024:
        messagebox.showwarning("Arquivo muito grande", "Selecione uma imagem com no maximo 10 MB.")
        return
    value.set(filename)


def vehicle_field_value(field):
    if isinstance(field, tk.Text):
        return field.get("1.0", "end").strip()
    if isinstance(field, tk.StringVar):
        return field.get().strip()
    return field.get().strip()


def collect_vehicle_form_values(fields):
    values = {}
    for key, field in fields.items():
        if key == "veiculo_de_rede":
            values[key] = "Sim" if field.get() else "Nao"
        else:
            values[key] = vehicle_field_value(field)
    return values


def save_vehicle_form(app, window, fields, vehicle=None):
    values = collect_vehicle_form_values(fields)
    network_vehicle = values.get("veiculo_de_rede") == "Sim"
    apply_network_flags(values, network_vehicle)
    values["tipo_veiculo"] = normalize_vehicle_type(values.get("tipo_veiculo"))

    labels = {
        "tipo_veiculo": "Tipo de veiculo",
        "status": "Status",
        "marca": "Marca",
        "modelo": "Modelo",
        "ano": "Ano",
        "cor": "Cor",
        "placa": "Placa",
        "combustivel": "Combustivel",
        "renavam": "RENAVAM",
        "chassi": "Chassi",
        "capa": "Imagem de capa",
        "observacoes": "Observacoes do veiculo",
    }
    if network_vehicle:
        labels.update(
            {
                "valor_km": "Valor por KM",
                "valor_hora": "Valor por hora",
                "tarifa_base": "Tarifa base",
                "valor_minimo": "Valor minimo",
                "distancia_minima": "Distancia minima",
                "tipo_cobranca": "Tipo de cobranca",
                "tolerancia_min": "Tolerancia",
                "valor_hora_espera": "Valor/hora espera",
                "fracao_min": "Cobranca por fracao",
                "multiplicador_ida_volta": "Multiplicador ida e volta",
                "preco_fixo_rota": "Preco fixo por rota",
                "taxa_noturna": "Taxa noturna",
                "taxa_aeroporto": "Taxa aeroporto",
                "pedagio": "Pedagio",
                "taxas_extras": "Taxas extras",
            }
        )
    for image_key in [
        "img_dianteira",
        "img_traseira",
        "img_lateral_esquerda",
        "img_lateral_direita",
        "img_externa_1",
        "img_externa_2",
        "img_externa_3",
        "img_externa_4",
        "img_interna_1",
        "img_interna_2",
        "img_interna_3",
        "img_interna_4",
    ]:
        labels[image_key] = image_key.replace("img_", "Imagem ").replace("_", " ")

    for key, label in labels.items():
        if not values.get(key):
            messagebox.showwarning("Campo obrigatorio", f"Informe: {label}.", parent=window)
            return

    for key, label in labels.items():
        if key == "capa" or key.startswith("img_"):
            if not os.path.exists(values[key]):
                messagebox.showwarning("Imagem obrigatoria", f"Selecione uma imagem valida para: {label}.", parent=window)
                return
            if os.path.getsize(values[key]) > 10 * 1024 * 1024:
                messagebox.showwarning("Arquivo muito grande", f"A imagem de {label} deve ter no maximo 10 MB.", parent=window)
                return

    cover_size = read_image_size(values["capa"])
    if cover_size and cover_size != (1220, 880):
        messagebox.showwarning("Capa invalida", "A capa deve ter exatamente 1220x880 px.", parent=window)
        return

    if vehicle is None:
        values["id"] = next_entity_id("veh", getattr(app, "vehicles", []))
        app.vehicles.insert(0, values)
    else:
        values["id"] = vehicle.get("id", values.get("id", ""))
        if vehicle.get("uuid"):
            values["uuid"] = vehicle["uuid"]
        vehicle.update(values)
    app.save_state()
    window.destroy()
    app.show_page("VEICULOS")


def read_image_size(path):
    try:
        with open(path, "rb") as file:
            header = file.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                return struct.unpack(">II", header[16:24])
            if header[:2] == b"\xff\xd8":
                file.seek(2)
                while True:
                    marker = file.read(2)
                    if len(marker) < 2:
                        return None
                    while marker[0] != 0xFF:
                        marker = marker[1:] + file.read(1)
                    code = marker[1]
                    size = struct.unpack(">H", file.read(2))[0]
                    if code in (0xC0, 0xC2):
                        data = file.read(size - 2)
                        return struct.unpack(">HH", data[1:5])[::-1]
                    file.seek(size - 2, 1)
    except OSError:
        return None
    return None



def render_system(parent, key):
    if key == "CONFIGURACOES":
        title, subtitle, action = SYSTEM_CONFIG["header"]
        header_panel(parent, title, subtitle, action)
        summary_cards(parent, SYSTEM_CONFIG["cards"])
        settings_grid(parent, SYSTEM_CONFIG["settings"])
        return

    title, subtitle, action = SYSTEM_AUTOMATIONS["header"]
    header_panel(parent, title, subtitle, action)
    summary_cards(parent, SYSTEM_AUTOMATIONS["cards"])
    data_table(parent, SYSTEM_AUTOMATIONS["columns"], SYSTEM_AUTOMATIONS["rows"])
