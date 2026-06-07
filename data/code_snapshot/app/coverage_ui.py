"""Interface hierarquica da Abrangencia Nacional: IBGE + pontos operacionais."""
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from .coverage_map import open_coverage_map
from .geography import (
    OPERATIONAL_POINT_STATUSES,
    OPERATIONAL_POINT_TYPES,
    coverage_metrics,
    ensure_operational_points,
    next_operational_point_id,
    normalize_operational_point,
    operational_point_label,
    points_for_city,
)
from . import ibge
from .theme import COLORS, FONTS, panel_frame, styled_button


def render_abrangencia(parent, app):
    parent.configure(bg=COLORS["bg"])
    ensure_operational_points(app)

    if not hasattr(app, "_abrangencia_ctx"):
        app._abrangencia_ctx = {
            "selected_state": None,
            "selected_city": None,
            "states": [],
            "cities": [],
        }

    ctx = app._abrangencia_ctx
    for widget in parent.winfo_children():
        widget.destroy()

    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))

    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(
        title_box,
        text="Abrangencia Nacional",
        bg=COLORS["bg"],
        fg=COLORS["text"],
        font=FONTS["title"],
    ).pack(anchor="w")
    tk.Label(
        title_box,
        text="Estrutura geografica oficial da plataforma. Estados e cidades vêm do IBGE; pontos operacionais sao cadastrados manualmente.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=760,
        justify="left",
    ).pack(anchor="w", pady=(2, 0))

    actions = tk.Frame(header, bg=COLORS["bg"])
    actions.pack(side="right", anchor="n")
    styled_button(actions, "Ver mapa de abrangencia", style="primary", command=lambda: open_coverage_map(app)).pack(side="left", padx=(0, 8))
    styled_button(actions, "Atualizar IBGE", style="secondary", command=lambda: refresh_ibge(app, parent)).pack(side="left", padx=(0, 8))
    styled_button(
        actions,
        "+ Ponto operacional",
        style="success",
        size="lg",
        command=lambda: open_operational_point_form(app, parent),
    ).pack(side="left")

    metrics = coverage_metrics(app.operational_points)
    cards = tk.Frame(parent, bg=COLORS["bg"])
    cards.pack(fill="x", pady=(0, 12))
    _metric_card(cards, "Estados IBGE", "27", "Fonte oficial sincronizada").pack(side="left", fill="x", expand=True, padx=(0, 8))
    _metric_card(cards, "Pontos operacionais", str(metrics["total_points"]), f'{metrics["active_points"]} ativos').pack(side="left", fill="x", expand=True, padx=(0, 8))
    _metric_card(cards, "Estados com pontos", str(metrics["states_with_points"]), "Cobertura cadastrada").pack(side="left", fill="x", expand=True, padx=(0, 8))
    _metric_card(cards, "Cidades com pontos", str(metrics["cities_with_points"]), "Distribuicao operacional").pack(side="left", fill="x", expand=True)

    status = tk.Label(parent, text="Carregando estados do IBGE...", bg=COLORS["bg"], fg=COLORS["muted"], font=FONTS["small"])
    status.pack(anchor="w", pady=(0, 8))

    body = tk.Frame(parent, bg=COLORS["bg"])
    body.pack(fill="both", expand=True)
    body.grid_columnconfigure(0, weight=1, uniform="geo")
    body.grid_columnconfigure(1, weight=1, uniform="geo")
    body.grid_columnconfigure(2, weight=2, uniform="geo")
    body.grid_rowconfigure(0, weight=1)

    states_box = _panel(body, "Nivel 1 - Estados (IBGE)", 0)
    cities_box = _panel(body, "Nivel 2 - Cidades (IBGE)", 1)
    points_box = _panel(body, "Nivel 3 - Pontos operacionais", 2)

    ctx["states_list"] = tk.Listbox(
        states_box,
        bg=COLORS["panel"],
        fg=COLORS["text"],
        selectbackground=COLORS["primary_soft"],
        selectforeground=COLORS["primary_dark"],
        relief="flat",
        highlightthickness=1,
        highlightbackground=COLORS["line"],
        font=FONTS["body"],
        activestyle="none",
    )
    ctx["states_list"].pack(fill="both", expand=True, padx=10, pady=(0, 10))
    ctx["states_list"].bind("<<ListboxSelect>>", lambda _event: on_state_selected(app, parent))

    ctx["cities_list"] = tk.Listbox(
        cities_box,
        bg=COLORS["panel"],
        fg=COLORS["text"],
        selectbackground=COLORS["primary_soft"],
        selectforeground=COLORS["primary_dark"],
        relief="flat",
        highlightthickness=1,
        highlightbackground=COLORS["line"],
        font=FONTS["body"],
        activestyle="none",
    )
    ctx["cities_list"].pack(fill="both", expand=True, padx=10, pady=(0, 10))
    ctx["cities_list"].bind("<<ListboxSelect>>", lambda _event: on_city_selected(app, parent))

    points_frame = tk.Frame(points_box, bg=COLORS["panel"])
    points_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    columns = ("nome", "tipo", "endereco", "status")
    ctx["points_tree"] = ttk.Treeview(points_frame, columns=columns, show="headings", style="Custom.Treeview", height=14)
    ctx["points_tree"].heading("nome", text="Nome")
    ctx["points_tree"].heading("tipo", text="Tipo")
    ctx["points_tree"].heading("endereco", text="Endereco")
    ctx["points_tree"].heading("status", text="Status")
    ctx["points_tree"].column("nome", width=180, anchor="w")
    ctx["points_tree"].column("tipo", width=120, anchor="w")
    ctx["points_tree"].column("endereco", width=220, anchor="w")
    ctx["points_tree"].column("status", width=90, anchor="w")
    y_scroll = ttk.Scrollbar(points_frame, orient="vertical", command=ctx["points_tree"].yview)
    ctx["points_tree"].configure(yscrollcommand=y_scroll.set)
    ctx["points_tree"].grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    points_frame.grid_rowconfigure(0, weight=1)
    points_frame.grid_columnconfigure(0, weight=1)

    point_actions = tk.Frame(points_box, bg=COLORS["panel"])
    point_actions.pack(fill="x", padx=10, pady=(0, 10))
    styled_button(point_actions, "Editar", style="outline_primary", size="sm", command=lambda: edit_selected_point(app, parent)).pack(side="left", padx=(0, 6))
    styled_button(point_actions, "Excluir", style="outline_danger", size="sm", command=lambda: delete_selected_point(app, parent)).pack(side="left")

    ctx["status_label"] = status
    load_states_async(app, parent)


def _panel(parent, title, column):
    box = panel_frame(parent)
    box.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
    tk.Label(box, text=title, bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["subtitle"]).pack(anchor="w", padx=10, pady=(10, 6))
    content = tk.Frame(box, bg=COLORS["panel"])
    content.pack(fill="both", expand=True)
    return content


def _metric_card(parent, title, value, hint):
    card = panel_frame(parent)
    tk.Label(card, text=title, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(10, 0))
    tk.Label(card, text=value, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=12)
    tk.Label(card, text=hint, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(0, 10))
    return card


def load_states_async(app, parent, force_refresh=False):
    ctx = app._abrangencia_ctx
    ctx["status_label"].configure(text="Sincronizando estados com o IBGE...")

    def worker():
        states = ibge.get_states(force_refresh=force_refresh)
        app.after(0, lambda: _apply_states(app, parent, states))

    threading.Thread(target=worker, daemon=True).start()


def _apply_states(app, parent, states):
    ctx = app._abrangencia_ctx
    ctx["states"] = states
    ctx["states_list"].delete(0, "end")
    for state in states:
        ctx["states_list"].insert("end", f'{state["nome"]} ({state["sigla"]})')

    ctx["status_label"].configure(text=f"{len(states)} estados sincronizados via IBGE.")
    if ctx.get("selected_state"):
        _reselect_state(app)


def _reselect_state(app):
    ctx = app._abrangencia_ctx
    selected = ctx.get("selected_state")
    if not selected:
        return
    for index, state in enumerate(ctx["states"]):
        if state.get("sigla") == selected.get("sigla"):
            ctx["states_list"].selection_clear(0, "end")
            ctx["states_list"].selection_set(index)
            ctx["states_list"].see(index)
            load_cities_async(app, app.winfo_toplevel(), selected.get("sigla"))
            break


def refresh_ibge(app, parent):
    load_states_async(app, parent, force_refresh=True)
    selected = app._abrangencia_ctx.get("selected_state")
    if selected:
        load_cities_async(app, parent, selected.get("sigla"), force_refresh=True)


def on_state_selected(app, parent):
    ctx = app._abrangencia_ctx
    selection = ctx["states_list"].curselection()
    if not selection:
        return
    state = ctx["states"][selection[0]]
    ctx["selected_state"] = state
    ctx["selected_city"] = None
    ctx["cities_list"].delete(0, "end")
    ctx["cities"] = []
    refresh_points_tree(app)
    load_cities_async(app, parent, state.get("sigla"))


def load_cities_async(app, parent, uf, force_refresh=False):
    ctx = app._abrangencia_ctx
    ctx["status_label"].configure(text=f"Carregando cidades de {uf} no IBGE...")

    def worker():
        cities = ibge.get_municipalities(uf, force_refresh=force_refresh)
        app.after(0, lambda: _apply_cities(app, cities, uf))

    threading.Thread(target=worker, daemon=True).start()


def _apply_cities(app, cities, uf):
    ctx = app._abrangencia_ctx
    ctx["cities"] = cities
    ctx["cities_list"].delete(0, "end")
    for city in cities:
        ctx["cities_list"].insert("end", city.get("nome", ""))

    state = ctx.get("selected_state") or {}
    ctx["status_label"].configure(
        text=f'{len(cities)} cidades de {state.get("nome", uf)} sincronizadas via IBGE.'
    )
    if ctx.get("selected_city"):
        _reselect_city(app)
    else:
        refresh_points_tree(app)


def _reselect_city(app):
    ctx = app._abrangencia_ctx
    selected = ctx.get("selected_city")
    if not selected:
        return
    for index, city in enumerate(ctx["cities"]):
        if int(city.get("id") or 0) == int(selected.get("id") or 0):
            ctx["cities_list"].selection_clear(0, "end")
            ctx["cities_list"].selection_set(index)
            ctx["cities_list"].see(index)
            refresh_points_tree(app)
            break


def on_city_selected(app, parent):
    ctx = app._abrangencia_ctx
    selection = ctx["cities_list"].curselection()
    if not selection:
        return
    ctx["selected_city"] = ctx["cities"][selection[0]]
    refresh_points_tree(app)


def refresh_points_tree(app):
    ctx = app._abrangencia_ctx
    tree = ctx["points_tree"]
    for item in tree.get_children():
        tree.delete(item)

    points = app.operational_points
    selected_city = ctx.get("selected_city")
    selected_state = ctx.get("selected_state")

    if selected_city and selected_state:
        points = points_for_city(points, selected_state.get("sigla"), selected_city.get("id"))
        subtitle = f'{selected_city.get("nome", "")} / {selected_state.get("sigla", "")}'
    elif selected_state:
        uf = selected_state.get("sigla", "")
        points = [point for point in points if point.get("estado_uf") == uf]
        subtitle = f'Todos os pontos em {selected_state.get("nome", "")}'
    else:
        subtitle = "Selecione um estado e uma cidade"

    for point in points:
        tree.insert(
            "",
            "end",
            iid=point.get("id"),
            values=(
                point.get("nome", ""),
                point.get("tipo", ""),
                point.get("endereco", ""),
                point.get("status", ""),
            ),
        )

    ctx["status_label"].configure(text=subtitle)


def get_selected_point(app):
    ctx = app._abrangencia_ctx
    selection = ctx["points_tree"].selection()
    if not selection:
        return None
    point_id = selection[0]
    return next((point for point in app.operational_points if point.get("id") == point_id), None)


def edit_selected_point(app, parent):
    point = get_selected_point(app)
    if not point:
        messagebox.showwarning("Abrangencia", "Selecione um ponto operacional na lista.", parent=app)
        return
    open_operational_point_form(app, parent, point)


def delete_selected_point(app, parent):
    point = get_selected_point(app)
    if not point:
        messagebox.showwarning("Abrangencia", "Selecione um ponto operacional para excluir.", parent=app)
        return
    if not messagebox.askyesno("Excluir ponto", f'Excluir "{point.get("nome", "")}"?', parent=app):
        return
    app.operational_points = [item for item in app.operational_points if item.get("id") != point.get("id")]
    app.save_state()
    if hasattr(app, "_abrangencia_ctx") and app._abrangencia_ctx.get("points_tree"):
        refresh_points_tree(app)
    else:
        render_abrangencia(parent, app)


def open_operational_point_form(app, parent, point=None):
    ctx = app._abrangencia_ctx
    selected_state = ctx.get("selected_state")
    selected_city = ctx.get("selected_city")
    if not point and (not selected_state or not selected_city):
        messagebox.showwarning(
            "Abrangencia",
            "Selecione um estado e uma cidade do IBGE antes de cadastrar um ponto operacional.",
            parent=app,
        )
        return

    window = tk.Toplevel(app)
    editing = point is not None
    window.title("Editar ponto operacional" if editing else "Novo ponto operacional")
    window.configure(bg=COLORS["bg"])
    window.geometry("640x620")
    window.minsize(640, 520)
    window.transient(app)
    window.grab_set()

    footer = tk.Frame(window, bg=COLORS["bg"])
    footer.pack(side="bottom", fill="x", padx=14, pady=(0, 14))
    styled_button(footer, "Cancelar", style="secondary", command=window.destroy).pack(side="right", padx=(8, 0))
    styled_button(
        footer,
        "Salvar",
        style="success",
        command=lambda: save_operational_point(app, parent, window, fields, point, state, city),
    ).pack(side="right")

    shell = panel_frame(window)
    shell.pack(fill="both", expand=True, padx=14, pady=(14, 0))

    tk.Label(shell, text="Ponto operacional", bg=COLORS["panel"], fg=COLORS["primary"], font=FONTS["heading"]).pack(anchor="w", padx=14, pady=(12, 4))
    tk.Label(
        shell,
        text="Somente aeroportos, hoteis, centros de eventos e hubs operacionais sao cadastrados manualmente.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=560,
        justify="left",
    ).pack(anchor="w", padx=14, pady=(0, 10))

    canvas = tk.Canvas(shell, bg=COLORS["panel"], highlightthickness=0)
    scrollbar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=(0, 12))
    canvas.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=(0, 12))

    form = tk.Frame(canvas, bg=COLORS["panel"])
    form_window = canvas.create_window((0, 0), window=form, anchor="nw")
    form.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(form_window, width=e.width))

    fields = {}
    _form_row(form, "Nome", fields, "nome", point.get("nome", "") if point else "")
    _form_combo(form, "Tipo", fields, "tipo", OPERATIONAL_POINT_TYPES, point.get("tipo") if point else OPERATIONAL_POINT_TYPES[0])

    state = selected_state or {}
    city = selected_city or {}
    if point:
        state_text = f'{point.get("estado_nome", "")} ({point.get("estado_uf", "")})'
        city_text = point.get("cidade_nome", "")
    else:
        state_text = f'{state.get("nome", "")} ({state.get("sigla", "")})'
        city_text = city.get("nome", "")

    _form_readonly(form, "Estado (IBGE)", state_text)
    _form_readonly(form, "Cidade (IBGE)", city_text)
    _form_row(form, "Endereco", fields, "endereco", point.get("endereco", "") if point else "")
    _form_row(form, "Observacoes", fields, "observacoes", point.get("observacoes", "") if point else "", height=3)
    _form_combo(form, "Status", fields, "status", OPERATIONAL_POINT_STATUSES, point.get("status") if point else "Operando")


def _form_row(parent, label, fields, key, value="", height=1):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["small"]).pack(anchor="w", pady=(4, 2))
    if height > 1:
        widget = tk.Text(parent, height=height, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=FONTS["body"])
        widget.pack(fill="x", ipady=4, pady=(0, 6))
        if value:
            widget.insert("1.0", value)
    else:
        widget = tk.Entry(parent, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=FONTS["body"])
        widget.pack(fill="x", ipady=6, pady=(0, 6))
        if value:
            widget.insert(0, value)
    fields[key] = widget


def _form_combo(parent, label, fields, key, values, current):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["small"]).pack(anchor="w", pady=(4, 2))
    widget = ttk.Combobox(parent, values=values, state="readonly", font=FONTS["body"])
    widget.set(current or values[0])
    widget.pack(fill="x", pady=(0, 6))
    fields[key] = widget


def _form_readonly(parent, label, value):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["small"]).pack(anchor="w", pady=(4, 2))
    tk.Label(parent, text=value, bg=COLORS["panel_alt"], fg=COLORS["text"], font=FONTS["body"], anchor="w", padx=8, pady=6).pack(fill="x", pady=(0, 6))


def _read_field(fields, key):
    widget = fields[key]
    if isinstance(widget, tk.Text):
        return widget.get("1.0", "end-1c").strip()
    return widget.get().strip()


def save_operational_point(app, parent, window, fields, point, state, city):
    nome = _read_field(fields, "nome")
    if not nome:
        messagebox.showwarning("Abrangencia", "Informe o nome do ponto operacional.", parent=window)
        return

    payload = normalize_operational_point(
        {
            "id": point.get("id") if point else next_operational_point_id(app.operational_points),
            "nome": nome,
            "tipo": fields["tipo"].get(),
            "estado_uf": (point or {}).get("estado_uf") or state.get("sigla", ""),
            "estado_nome": (point or {}).get("estado_nome") or state.get("nome", ""),
            "cidade_ibge_id": (point or {}).get("cidade_ibge_id") or city.get("id", 0),
            "cidade_nome": (point or {}).get("cidade_nome") or city.get("nome", ""),
            "endereco": _read_field(fields, "endereco"),
            "observacoes": _read_field(fields, "observacoes"),
            "status": fields["status"].get(),
            "legacy_coverage_id": (point or {}).get("legacy_coverage_id", ""),
            "criado_em": (point or {}).get("criado_em") or datetime.now().strftime("%d/%m/%Y %H:%M"),
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
    )

    updated = False
    for index, existing in enumerate(app.operational_points):
        if existing.get("id") == payload.get("id"):
            app.operational_points[index] = payload
            updated = True
            break
    if not updated:
        app.operational_points.append(payload)

    app.save_state()
    window.destroy()

    if hasattr(app, "_abrangencia_ctx") and app._abrangencia_ctx.get("points_tree"):
        refresh_points_tree(app)
        tree = app._abrangencia_ctx["points_tree"]
        point_id = payload.get("id")
        if point_id and tree.exists(point_id):
            tree.selection_set(point_id)
            tree.focus(point_id)
            tree.see(point_id)
    else:
        render_abrangencia(parent, app)

    messagebox.showinfo("Abrangencia", f'Ponto "{operational_point_label(payload)}" salvo com sucesso.', parent=app)
