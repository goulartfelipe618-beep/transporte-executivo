"""Seletor de origem/destino com Rede Operacional ou endereco manual."""
import tkinter as tk
from tkinter import ttk

from .operational_network import LOCATION_MODE_MANUAL, LOCATION_MODE_NETWORK, network_point_options, resolve_location
from .theme import COLORS


def add_location_picker(section, fields, prefix, label, row, app):
    tk.Label(section, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).grid(row=row, column=0, sticky="nw", padx=12, pady=8)

    box = tk.Frame(section, bg=COLORS["panel"])
    box.grid(row=row, column=1, sticky="ew", padx=12, pady=8)
    box.grid_columnconfigure(0, weight=1)

    mode = tk.StringVar(value=LOCATION_MODE_MANUAL)
    fields[f"{prefix}_modo"] = mode
    mode_line = tk.Frame(box, bg=COLORS["panel"])
    mode_line.pack(fill="x", pady=(0, 6))
    tk.Radiobutton(
        mode_line,
        text="Endereco livre",
        variable=mode,
        value=LOCATION_MODE_MANUAL,
        bg=COLORS["panel"],
        command=lambda: toggle_location_mode(fields, prefix),
    ).pack(side="left", padx=(0, 12))
    tk.Radiobutton(
        mode_line,
        text="Rede Operacional",
        variable=mode,
        value=LOCATION_MODE_NETWORK,
        bg=COLORS["panel"],
        command=lambda: toggle_location_mode(fields, prefix),
    ).pack(side="left")

    manual = tk.Entry(box, bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 10))
    manual.pack(fill="x", ipady=6)
    fields[prefix] = manual

    options = network_point_options(app)
    fields[f"{prefix}_network_options"] = options
    combo = ttk.Combobox(box, values=[item["label"] for item in options], state="readonly", font=("Segoe UI", 10))
    combo.pack(fill="x", pady=(6, 0))
    combo.pack_forget()
    fields[f"{prefix}_network_combo"] = combo
    return box


def toggle_location_mode(fields, prefix):
    manual = fields[prefix]
    combo = fields[f"{prefix}_network_combo"]
    mode = fields[f"{prefix}_modo"].get()
    if mode == LOCATION_MODE_NETWORK:
        manual.pack_forget()
        combo.pack(fill="x", pady=(6, 0))
    else:
        combo.pack_forget()
        manual.pack(fill="x", ipady=6)


def read_location(app, fields, prefix):
    mode = fields[f"{prefix}_modo"].get()
    manual_widget = fields[prefix]
    manual_text = manual_widget.get().strip() if isinstance(manual_widget, tk.Entry) else str(manual_widget)
    point_id = ""
    if mode == LOCATION_MODE_NETWORK:
        selected = fields[f"{prefix}_network_combo"].get()
        for option in fields.get(f"{prefix}_network_options", []):
            if option.get("label") == selected:
                point_id = option.get("id", "")
                break
    return resolve_location(app, mode, point_id, manual_text)


def reservation_location_fields(location, prefix):
    location = location or {}
    return {
        f"{prefix}_modo": location.get("modo", LOCATION_MODE_MANUAL),
        f"{prefix}_point_id": location.get("point_id", ""),
        f"{prefix}_nome": location.get("nome", ""),
        f"{prefix}_tipo": location.get("tipo", ""),
        f"{prefix}_cidade": location.get("cidade", ""),
        f"{prefix}_estado": location.get("estado", ""),
        f"{prefix}_endereco": location.get("endereco", ""),
        f"{prefix}_display": location.get("display", ""),
        f"{prefix}_website_path": location.get("website_path", ""),
    }
