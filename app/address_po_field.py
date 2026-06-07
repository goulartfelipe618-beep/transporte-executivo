"""Campo de endereco com modo Ponto Operacional (PO) — Abrangencia."""
import tkinter as tk
from tkinter import ttk

from .components import apply_input_rules, resolve_widget_value
from .geography import ensure_operational_points, operational_point_label
from .theme import COLORS


def operational_point_address_text(point):
    if not point:
        return ""
    nome = str(point.get("nome", "")).strip()
    endereco = str(point.get("endereco", "")).strip()
    cidade = str(point.get("cidade_nome", "")).strip()
    uf = str(point.get("estado_uf", "")).strip()
    location = f"{cidade}/{uf}".strip("/")
    if nome and endereco:
        base = f"{nome} — {endereco}"
    else:
        base = nome or endereco
    if location and base:
        return f"{base} ({location})"
    return base or location


def selectable_operational_points(app):
    ensure_operational_points(app)
    points = []
    for point in app.operational_points:
        if point.get("status") == "Pausado":
            continue
        points.append(point)
    return sorted(points, key=lambda item: operational_point_label(item).lower())


def add_po_address_field(parent, fields, po_controls, key, label, row, app, placeholder=""):
    tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).grid(
        row=row, column=0, sticky="w", padx=12, pady=5
    )

    row_frame = tk.Frame(parent, bg=COLORS["panel"])
    row_frame.grid(row=row, column=1, sticky="ew", padx=12, pady=5)
    row_frame.grid_columnconfigure(1, weight=1)

    po_side = tk.Frame(row_frame, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground="#D3DAE3")
    po_side.grid(row=0, column=0, sticky="ns", padx=(0, 8))

    tk.Label(po_side, text="PO", bg=COLORS["panel_alt"], fg=COLORS["primary"], font=("Segoe UI Semibold", 8)).pack(
        padx=8, pady=(6, 0)
    )

    po_active = tk.BooleanVar(value=False)
    toggle_btn = tk.Button(
        po_side,
        text="Ativar",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        activebackground=COLORS["primary_soft"],
        activeforeground=COLORS["primary_dark"],
        relief="solid",
        bd=1,
        font=("Segoe UI Semibold", 8),
        padx=6,
        pady=3,
        cursor="hand2",
        command=lambda: _toggle_po_mode(key, po_controls),
    )
    toggle_btn.pack(padx=6, pady=(4, 8))

    value_host = tk.Frame(row_frame, bg=COLORS["panel"])
    value_host.grid(row=0, column=1, sticky="ew")
    value_host.grid_columnconfigure(0, weight=1)

    manual = tk.Entry(value_host, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
    manual.grid(row=0, column=0, sticky="ew")
    apply_input_rules(manual, field_key=key, placeholder=placeholder, label=label)

    po_box = tk.Frame(value_host, bg=COLORS["panel"])
    po_search = tk.Entry(po_box, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 9))
    po_search.pack(fill="x", pady=(0, 4))
    apply_input_rules(po_search, placeholder="Pesquisar ponto operacional...", label="Pesquisar PO")
    po_combo = ttk.Combobox(po_box, state="readonly", font=("Segoe UI", 9))
    po_combo.pack(fill="x")

    ctrl = {
        "active": po_active,
        "toggle_btn": toggle_btn,
        "manual": manual,
        "po_box": po_box,
        "search": po_search,
        "combo": po_combo,
        "options": [],
        "labels": [],
        "app": app,
    }
    po_controls[key] = ctrl
    fields[key] = manual

    po_search.bind("<KeyRelease>", lambda _event, field_key=key: _filter_po_options(field_key, po_controls))
    po_combo.bind("<<ComboboxSelected>>", lambda _event, field_key=key: _sync_po_selection(field_key, po_controls))

    _reload_po_options(key, po_controls)
    return manual


def _reload_po_options(key, po_controls):
    ctrl = po_controls[key]
    app = ctrl["app"]
    points = selectable_operational_points(app)
    ctrl["options"] = points
    ctrl["labels"] = [operational_point_label(point) for point in points]
    _filter_po_options(key, po_controls)


def _filter_po_options(key, po_controls):
    ctrl = po_controls[key]
    search = ctrl["search"].get().strip().lower()
    labels = []
    options = []
    for point, label in zip(ctrl["options"], ctrl["labels"]):
        haystack = " ".join(
            [
                label.lower(),
                str(point.get("nome", "")).lower(),
                str(point.get("endereco", "")).lower(),
                str(point.get("cidade_nome", "")).lower(),
                str(point.get("estado_uf", "")).lower(),
            ]
        )
        if not search or search in haystack:
            labels.append(label)
            options.append(point)
    ctrl["filtered_options"] = options
    ctrl["combo"].configure(values=labels)
    if labels:
        current = ctrl["combo"].get()
        if current not in labels:
            ctrl["combo"].set(labels[0])
    else:
        ctrl["combo"].set("")


def _sync_po_selection(key, po_controls):
    ctrl = po_controls[key]
    label = ctrl["combo"].get()
    options = ctrl.get("filtered_options") or ctrl["options"]
    ctrl["selected_point"] = None
    for point in options:
        if operational_point_label(point) == label:
            ctrl["selected_point"] = point
            break


def _toggle_po_mode(key, po_controls):
    ctrl = po_controls[key]
    active = not ctrl["active"].get()
    ctrl["active"].set(active)
    if active:
        _reload_po_options(key, po_controls)
        ctrl["manual"].grid_remove()
        ctrl["po_box"].grid(row=0, column=0, sticky="ew")
        ctrl["toggle_btn"].configure(text="Manual", bg=COLORS["primary_soft"], fg=COLORS["primary_dark"])
        if not ctrl["combo"].get() and ctrl["combo"]["values"]:
            ctrl["combo"].set(ctrl["combo"]["values"][0])
            _sync_po_selection(key, po_controls)
        return

    ctrl["po_box"].grid_remove()
    ctrl["manual"].grid(row=0, column=0, sticky="ew")
    ctrl["toggle_btn"].configure(text="Ativar", bg=COLORS["panel"], fg=COLORS["text"])
    ctrl["selected_point"] = None


def resolve_address_field(po_controls, key, fields=None):
    ctrl = po_controls.get(key)
    if not ctrl:
        widget = (fields or {}).get(key)
        return (resolve_widget_value(widget) if widget else ""), None, "manual"

    if ctrl["active"].get():
        _sync_po_selection(key, po_controls)
        point = ctrl.get("selected_point")
        if not point and ctrl["combo"].get():
            label = ctrl["combo"].get()
            for candidate in ctrl.get("filtered_options") or ctrl["options"]:
                if operational_point_label(candidate) == label:
                    point = candidate
                    break
        if not point:
            return "", None, "rede"
        return operational_point_address_text(point), point.get("id"), "rede"

    return resolve_widget_value(ctrl["manual"]), None, "manual"


def collect_address_values(po_controls, keys):
    payload = {}
    for key in keys:
        text, point_id, mode = resolve_address_field(po_controls, key)
        payload[key] = text
        payload[f"{key}_po_id"] = point_id or ""
        payload[f"{key}_modo"] = mode
    return payload
