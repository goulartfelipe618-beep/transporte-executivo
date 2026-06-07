import re
import tkinter as tk
from tkinter import messagebox, ttk

from .theme import COLORS, FONTS, panel_frame, styled_button

PLACEHOLDER_COLOR = "#94A3B8"
DATE_MASK_TEMPLATE = "__/__/____"
PHONE_MASK_TEMPLATE = "(__) _ ____-____"
TIME_MASK_TEMPLATE = "__:__"
EMAIL_PLACEHOLDER = "email@dominio.com"

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

DATE_FIELD_KEYS = frozenset(
    {
        "data",
        "volta_data",
        "hora_data",
        "nascimento",
        "validade_cnh",
        "validade",
        "data_de",
        "data_ate",
        "data_nascimento",
    }
)

CPF_CNPJ_FIELD_KEYS = frozenset(
    {
        "cpf",
        "cnpj",
        "documento",
        "cpf_cnpj",
        "cpf_titular",
        "cnpj_opcional",
        "cnpj_contrato",
        "cnh",
        "cep",
    }
)

PHONE_FIELD_KEYS = frozenset(
    {
        "telefone",
        "telefone_2",
        "telefone_contrato",
        "whatsapp_contrato",
        "contato",
        "whatsapp",
    }
)

EMAIL_FIELD_KEYS = frozenset(
    {
        "email",
        "e-mail",
        "email_oficial",
    }
)

TIME_FIELD_KEYS = frozenset(
    {
        "hora",
        "volta_hora",
        "hora_horario",
    }
)

LOWERCASE_FIELD_KEYS = frozenset(
    {
        "email",
        "e-mail",
        "email_oficial",
        "senha",
        "password",
        "token",
        "dominio_permitido",
        "portal_link",
        "link",
        "pix_chave",
        "website",
        "url",
        "activation_token",
    }
)


def _digits_only(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _format_date_mask(digits):
    digits = digits[:8]
    day = digits[0:2].ljust(2, "_")
    month = digits[2:4].ljust(2, "_")
    year = digits[4:8].ljust(4, "_")
    return f"{day}/{month}/{year}"


def is_date_field(field_key="", placeholder="", label=""):
    key = str(field_key or "").lower()
    if key in DATE_FIELD_KEYS:
        return True
    blob = f"{placeholder} {label}".lower()
    return "dd/mm" in blob


def is_cpf_cnpj_field(field_key="", label=""):
    key = str(field_key or "").lower()
    if key in CPF_CNPJ_FIELD_KEYS:
        return True
    blob = str(label or "").lower()
    return "cpf" in blob or "cnpj" in blob


def is_phone_field(field_key="", label=""):
    key = str(field_key or "").lower()
    if key in PHONE_FIELD_KEYS:
        return True
    blob = str(label or "").lower()
    return "telefone" in blob or "whatsapp" in blob


def is_email_field(field_key="", label=""):
    key = str(field_key or "").lower()
    if key in EMAIL_FIELD_KEYS:
        return True
    blob = str(label or "").lower()
    return "email" in blob or "e-mail" in blob


def is_time_field(field_key="", placeholder="", label=""):
    key = str(field_key or "").lower()
    if key in TIME_FIELD_KEYS:
        return True
    blob = f"{placeholder} {label}".lower()
    return "--:--" in blob or blob.strip() == "hora"


def is_valid_email(value):
    return bool(EMAIL_PATTERN.match(str(value or "").strip()))


def _format_phone_mask(digits):
    digits = digits[:11]
    area = digits[0:2].ljust(2, "_")
    first = digits[2:3] if len(digits) > 2 else "_"
    mid = digits[3:7].ljust(4, "_") if len(digits) > 3 else "____"
    end = digits[7:11].ljust(4, "_") if len(digits) > 7 else "____"
    return f"({area}) {first} {mid}-{end}"


def _format_time_mask(digits):
    digits = digits[:4]
    hours = digits[0:2].ljust(2, "_")
    minutes = digits[2:4].ljust(2, "_")
    return f"{hours}:{minutes}"


def _bind_digit_mask(widget, *, max_digits, formatter, template, flag_name):
    setattr(widget, flag_name, True)
    widget._no_uppercase = True

    def _apply(digits):
        formatted = formatter(digits) if digits else template
        widget.delete(0, "end")
        widget.insert(0, formatted)
        cursor = 0
        for index, char in enumerate(formatted):
            if char.isdigit():
                cursor = index + 1
        widget.icursor(cursor if digits else 0)
        widget.configure(fg=COLORS["text"] if digits else PLACEHOLDER_COLOR)

    def on_focus_in(_event):
        if not _digits_only(widget.get()):
            _apply("")

    def on_focus_out(_event):
        if not _digits_only(widget.get()):
            _apply("")

    def on_key(event):
        if event.keysym in {"Left", "Right", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return
        if event.keysym in {"BackSpace", "Delete"}:
            digits = _digits_only(widget.get())
            if event.keysym == "BackSpace":
                digits = digits[:-1]
            else:
                digits = ""
            _apply(digits)
            return "break"
        if event.char and event.char.isdigit():
            digits = _digits_only(widget.get())
            if len(digits) < max_digits:
                digits += event.char
            _apply(digits)
            return "break"
        if event.char:
            return "break"

    widget.bind("<FocusIn>", on_focus_in, add="+")
    widget.bind("<FocusOut>", on_focus_out, add="+")
    widget.bind("<Key>", on_key, add="+")
    initial = _digits_only(getattr(widget, "_initial_mask_value", ""))
    _apply(initial)


def setup_digits_only(widget, *, max_digits=14, initial_value=""):
    widget._digits_only_field = True
    widget._no_uppercase = True
    widget._max_digits = max_digits

    def _apply(digits):
        digits = digits[:max_digits]
        widget.delete(0, "end")
        if digits:
            widget.insert(0, digits)
            widget.configure(fg=COLORS["text"])
        widget.icursor(tk.END)

    def on_key(event):
        if event.keysym in {"Left", "Right", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return
        if event.keysym in {"BackSpace", "Delete"}:
            digits = _digits_only(widget.get())
            if event.keysym == "BackSpace":
                digits = digits[:-1]
            else:
                digits = ""
            _apply(digits)
            return "break"
        if event.char and event.char.isdigit():
            digits = _digits_only(widget.get())
            if len(digits) < max_digits:
                digits += event.char
            _apply(digits)
            return "break"
        if event.char:
            return "break"

    widget.bind("<Key>", on_key, add="+")
    initial = _digits_only(initial_value)
    if initial:
        _apply(initial)


def setup_phone_mask(widget, *, initial_value=""):
    widget._initial_mask_value = initial_value
    widget._phone_mask = True
    _bind_digit_mask(
        widget,
        max_digits=11,
        formatter=_format_phone_mask,
        template=PHONE_MASK_TEMPLATE,
        flag_name="_phone_mask",
    )


def setup_time_mask(widget, *, initial_value=""):
    widget._initial_mask_value = initial_value
    widget._time_mask = True
    _bind_digit_mask(
        widget,
        max_digits=4,
        formatter=_format_time_mask,
        template=TIME_MASK_TEMPLATE,
        flag_name="_time_mask",
    )


def setup_email_input(widget, *, initial_value="", placeholder=EMAIL_PLACEHOLDER):
    widget._email_input = True
    widget._no_uppercase = True

    def on_key(event):
        if event.keysym in {"Left", "Right", "Tab", "BackSpace", "Delete", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return
        if not event.char:
            return
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@._%+-")
        if event.char not in allowed:
            return "break"

    def on_focus_out(_event):
        if getattr(widget, "_placeholder_active", False):
            return
        value = widget.get().strip()
        if not value:
            widget.configure(fg=PLACEHOLDER_COLOR)
            return
        if is_valid_email(value):
            widget.configure(fg=COLORS["text"])
        else:
            widget.configure(fg=COLORS["danger"])

    widget.bind("<Key>", on_key, add="+")
    widget.bind("<FocusOut>", on_focus_out, add="+")

    raw = str(initial_value or "").strip()
    if raw:
        widget.insert(0, raw.lower())
    else:
        setup_placeholder(widget, placeholder)


def set_input_value(widget, value=""):
    value = str(value or "").strip()
    if getattr(widget, "_date_mask", False):
        widget._initial_mask_value = value
        digits = _digits_only(value)
        widget.delete(0, "end")
        if digits:
            formatted = _format_date_mask(digits)
            widget.insert(0, formatted)
            widget.configure(fg=COLORS["text"])
        else:
            widget.insert(0, DATE_MASK_TEMPLATE)
            widget.configure(fg=PLACEHOLDER_COLOR)
        return
    if getattr(widget, "_phone_mask", False):
        digits = _digits_only(value)
        widget.delete(0, "end")
        if digits:
            widget.insert(0, _format_phone_mask(digits))
            widget.configure(fg=COLORS["text"])
        else:
            widget.insert(0, PHONE_MASK_TEMPLATE)
            widget.configure(fg=PLACEHOLDER_COLOR)
        return
    if getattr(widget, "_digits_only_field", False):
        digits = _digits_only(value)
        widget.delete(0, "end")
        if digits:
            widget.insert(0, digits)
        return
    if getattr(widget, "_time_mask", False):
        digits = _digits_only(value.replace(":", ""))
        widget.delete(0, "end")
        if digits:
            widget.insert(0, _format_time_mask(digits))
            widget.configure(fg=COLORS["text"])
        else:
            widget.insert(0, TIME_MASK_TEMPLATE)
            widget.configure(fg=PLACEHOLDER_COLOR)
        return
    if getattr(widget, "_email_input", False):
        widget.delete(0, "end")
        if value:
            widget.insert(0, value.lower())
            widget.configure(fg=COLORS["text"])
        else:
            setup_placeholder(widget, EMAIL_PLACEHOLDER)
        return
    widget.delete(0, "end")
    if value:
        widget.insert(0, value.upper() if not getattr(widget, "_no_uppercase", False) else value)


def setup_placeholder(widget, text):
    widget._placeholder_text = text
    is_text = isinstance(widget, tk.Text)
    normal_fg = COLORS["text"]

    def _get():
        return widget.get("1.0", "end-1c") if is_text else widget.get()

    def _set(value):
        if is_text:
            widget.delete("1.0", "end")
            if value:
                widget.insert("1.0", value)
        else:
            widget.delete(0, "end")
            if value:
                widget.insert(0, value)

    def _show():
        if not _get().strip():
            widget._placeholder_active = True
            _set(text)
            widget.configure(fg=PLACEHOLDER_COLOR)

    def _hide():
        if getattr(widget, "_placeholder_active", False):
            widget._placeholder_active = False
            _set("")
            widget.configure(fg=normal_fg)

    def on_focus_in(_event):
        _hide()

    def on_click(_event):
        if getattr(widget, "_placeholder_active", False):
            _hide()

    def on_focus_out(_event):
        if not _get().strip():
            _show()

    widget.bind("<FocusIn>", on_focus_in, add="+")
    widget.bind("<Button-1>", on_click, add="+")
    widget.bind("<FocusOut>", on_focus_out, add="+")
    _show()


def setup_date_mask(widget, *, initial_value=""):
    widget._date_mask = True
    widget._no_uppercase = True

    def _apply(digits):
        formatted = _format_date_mask(digits)
        widget.delete(0, "end")
        widget.insert(0, formatted)
        cursor = 0
        for index, char in enumerate(formatted):
            if char.isdigit():
                cursor = index + 1
            elif char == "/" and digits:
                cursor = index + 1
        widget.icursor(cursor if digits else 0)
        widget.configure(fg=COLORS["text"] if digits else PLACEHOLDER_COLOR)

    def on_focus_in(_event):
        digits = _digits_only(widget.get())
        if not digits:
            _apply("")

    def on_focus_out(_event):
        if not _digits_only(widget.get()):
            _apply("")

    def on_key(event):
        if event.keysym in {"Left", "Right", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return
        if event.keysym in {"BackSpace", "Delete"}:
            digits = _digits_only(widget.get())
            if event.keysym == "BackSpace":
                digits = digits[:-1]
            else:
                digits = ""
            _apply(digits)
            return "break"
        if event.char and event.char.isdigit():
            digits = _digits_only(widget.get())
            if len(digits) < 8:
                digits += event.char
            _apply(digits)
            return "break"
        if event.char:
            return "break"

    widget.bind("<FocusIn>", on_focus_in, add="+")
    widget.bind("<FocusOut>", on_focus_out, add="+")
    widget.bind("<Key>", on_key, add="+")

    initial_digits = _digits_only(initial_value)
    if initial_digits:
        _apply(initial_digits)
    else:
        _apply("")


def apply_input_rules(widget, *, field_key="", placeholder="", label="", value=""):
    widget._field_key = str(field_key or "")
    if field_key in LOWERCASE_FIELD_KEYS:
        widget._no_uppercase = True

    if is_date_field(field_key, placeholder, label):
        setup_date_mask(widget, initial_value=value or "")
        return
    if is_cpf_cnpj_field(field_key, label):
        max_digits = 8 if str(field_key or "").lower() == "cep" else 14
        setup_digits_only(widget, max_digits=max_digits, initial_value=_digits_only(value))
        return
    if is_phone_field(field_key, label):
        setup_phone_mask(widget, initial_value=value or "")
        return
    if is_email_field(field_key, label):
        setup_email_input(widget, initial_value=value or "", placeholder=placeholder or EMAIL_PLACEHOLDER)
        return
    if is_time_field(field_key, placeholder, label):
        setup_time_mask(widget, initial_value=_digits_only(value.replace(":", "")))
        return

    raw = str(value or "").strip()
    if raw:
        widget.insert(0, raw.upper() if not getattr(widget, "_no_uppercase", False) else raw)
    elif placeholder:
        setup_placeholder(widget, placeholder.upper())


def resolve_widget_value(widget):
    if getattr(widget, "_date_mask", False):
        digits = _digits_only(widget.get())
        if len(digits) != 8:
            return ""
        return f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"

    if getattr(widget, "_phone_mask", False):
        digits = _digits_only(widget.get())
        if len(digits) < 10:
            return ""
        return _format_phone_mask(digits)

    if getattr(widget, "_digits_only_field", False):
        return _digits_only(widget.get())

    if getattr(widget, "_time_mask", False):
        digits = _digits_only(widget.get())
        if len(digits) != 4:
            return ""
        return f"{digits[0:2]}:{digits[2:4]}"

    if getattr(widget, "_email_input", False):
        if getattr(widget, "_placeholder_active", False):
            return ""
        return widget.get().strip().lower()

    if getattr(widget, "_placeholder_active", False):
        return ""
    if isinstance(widget, tk.Text):
        return widget.get("1.0", "end-1c").strip()
    return widget.get().strip()


def validate_email_field(widget, *, parent=None, label="E-mail"):
    value = resolve_widget_value(widget)
    if not value:
        return False, f"Informe: {label}."
    if not is_valid_email(value):
        return False, f"{label} invalido. Use o formato nome@dominio.com"
    return True, ""


def parse_br_datetime(date_value, time_value=""):
    from datetime import datetime

    date_digits = _digits_only(date_value)
    if len(date_digits) != 8:
        return None
    time_digits = _digits_only(time_value)
    if len(time_digits) == 4:
        hour, minute = int(time_digits[0:2]), int(time_digits[2:4])
    else:
        hour, minute = 0, 0
    try:
        return datetime(
            int(date_digits[4:8]),
            int(date_digits[2:4]),
            int(date_digits[0:2]),
            hour,
            minute,
        )
    except ValueError:
        return None


def validate_future_datetime(date_value, time_value="", *, label="Data/hora", parent=None):
    from datetime import datetime

    parsed = parse_br_datetime(date_value, time_value)
    if not parsed:
        return False, f"{label} invalida. Use DD/MM/AAAA e HH:MM."
    if parsed < datetime.now():
        return False, f"{label} nao pode ser anterior a data e hora atuais."
    return True, ""


def enforce_uppercase(widget):
    if isinstance(widget, tk.Text):
        def on_key(_event):
            if getattr(widget, "_no_uppercase", False) or getattr(widget, "_placeholder_active", False):
                return
            content = widget.get("1.0", "end-1c")
            upper = content.upper()
            if content != upper:
                widget.delete("1.0", "end")
                widget.insert("1.0", upper)
        widget.bind("<KeyRelease>", on_key, add="+")
        return

    def on_key(_event):
        if not _should_uppercase(widget):
            return
        value = widget.get()
        upper = value.upper()
        if value != upper:
            pos = widget.index(tk.INSERT)
            widget.delete(0, "end")
            widget.insert(0, upper)
            widget.icursor(min(pos, len(upper)))

    widget.bind("<KeyRelease>", on_key, add="+")


def _should_uppercase(widget):
    if getattr(widget, "_no_uppercase", False):
        return False
    if getattr(widget, "_date_mask", False):
        return False
    if getattr(widget, "_phone_mask", False):
        return False
    if getattr(widget, "_digits_only_field", False):
        return False
    if getattr(widget, "_time_mask", False):
        return False
    if getattr(widget, "_email_input", False):
        return False
    if getattr(widget, "_placeholder_active", False):
        return False
    key = str(getattr(widget, "_field_key", "") or "").lower()
    if key in LOWERCASE_FIELD_KEYS:
        return False
    return True


def install_global_input_rules(root):
    def on_entry_keyrelease(event):
        widget = event.widget
        if not _should_uppercase(widget):
            return
        value = widget.get()
        upper = value.upper()
        if value != upper:
            pos = widget.index(tk.INSERT)
            widget.delete(0, "end")
            widget.insert(0, upper)
            widget.icursor(min(pos, len(upper)))

    def on_text_keyrelease(event):
        widget = event.widget
        if getattr(widget, "_no_uppercase", False) or getattr(widget, "_placeholder_active", False):
            return
        content = widget.get("1.0", "end-1c")
        upper = content.upper()
        if content != upper:
            widget.delete("1.0", "end")
            widget.insert("1.0", upper)

    root.bind_class("Entry", "<KeyRelease>", on_entry_keyrelease, add="+")
    root.bind_class("Text", "<KeyRelease>", on_text_keyrelease, add="+")


def header_panel(parent, title, subtitle, action_text="Novo registro", action_command=None):
    panel = panel_frame(parent)
    panel.pack(fill="x", pady=(0, 10))

    accent = tk.Frame(panel, bg=COLORS["primary"], width=4)
    accent.pack(side="left", fill="y")

    left = tk.Frame(panel, bg=COLORS["panel"])
    left.pack(side="left", fill="both", expand=True, padx=(14, 10), pady=12)
    tk.Label(left, text=title, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(left, text=subtitle, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["small"], wraplength=680, justify="left").pack(anchor="w", pady=(4, 0))

    styled_button(panel, action_text, style="primary", size="md", command=action_command).pack(side="right", padx=14, pady=12)


def summary_cards(parent, cards):
    row = tk.Frame(parent, bg=COLORS["bg"])
    row.pack(fill="x", pady=(0, 10))

    for index, item in enumerate(cards):
        card = panel_frame(row, bg=COLORS["panel"])
        card.pack(side="left", fill="x", expand=True, padx=(0 if index == 0 else 0, 10))

        tone = item.get("tone", "primary")
        accent_colors = {
            "primary": COLORS["primary"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "danger": COLORS["danger"],
        }
        accent = accent_colors.get(tone, COLORS["primary"])

        top = tk.Frame(card, bg=COLORS["panel"])
        top.pack(fill="x")
        tk.Frame(top, bg=accent, height=3).pack(fill="x")
        tk.Label(top, text=item["label"], bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=14, pady=(12, 0))
        tk.Label(top, text=item["value"], bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["mono_lg"]).pack(anchor="w", padx=14, pady=(2, 0))

        hint_color = accent_colors.get(tone, COLORS["success"])
        tk.Label(top, text=item["hint"], bg=COLORS["panel"], fg=hint_color, font=FONTS["tiny"]).pack(anchor="w", padx=14, pady=(2, 14))


def data_table(parent, columns, rows):
    table_box = panel_frame(parent)
    table_box.pack(fill="both", expand=True)

    tree = ttk.Treeview(table_box, columns=columns, show="headings", style="Custom.Treeview")
    for col in columns:
        tree.heading(col, text=str(col).upper())
        tree.column(col, anchor="w", width=120, minwidth=70, stretch=True)

    for row in rows:
        tree.insert("", "end", values=row)

    y_scroll = ttk.Scrollbar(table_box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=y_scroll.set)
    tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
    y_scroll.pack(side="right", fill="y", pady=6)


def settings_grid(parent, rows):
    box = panel_frame(parent)
    box.pack(fill="both", expand=True)

    head = tk.Frame(box, bg=COLORS["panel_alt"])
    head.pack(fill="x")
    tk.Label(head, text="Configuracoes principais", bg=COLORS["panel_alt"], fg=COLORS["primary"], font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=14, pady=(12, 10))

    for index, (section, label, value) in enumerate(rows):
        line = tk.Frame(box, bg=COLORS["panel"] if index % 2 == 0 else COLORS["panel_alt"])
        line.pack(fill="x", padx=10, pady=0)
        tk.Label(line, text=section, bg=COLORS["primary_soft"], fg=COLORS["primary"], width=16, font=("Segoe UI Semibold", 9), padx=10, pady=8).pack(side="left", padx=(4, 10), pady=6)
        tk.Label(line, text=label, bg=line.cget("bg"), fg=COLORS["text"], font=FONTS["small"]).pack(side="left", padx=4)
        tk.Label(line, text=value, bg=line.cget("bg"), fg=COLORS["warning"], font=("Consolas", 9, "bold")).pack(side="right", padx=12, pady=6)
