"""Tabelas responsivas (sem scroll horizontal) e barra de acoes."""
import tkinter as tk

from .theme import COLORS, styled_button

ACTION_STYLE_MAP = {
    "editar": "primary",
    "edit": "primary",
    "ver": "accent",
    "detalhes": "accent",
    "baixar": "warning",
    "baixar qr": "secondary",
    "copiar link": "accent",
    "copiar url": "accent",
    "token portal": "secondary",
    "portal": "accent",
    "configurar webhook": "primary",
    "excluir": "danger",
    "remover": "danger",
    "deletar": "danger",
    "confirmar": "success",
    "ativar": "success",
    "desativar": "warning",
}


def truncate_text(text, max_len=42):
    text = str(text or "").replace("\n", " · ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def action_style(label):
    return ACTION_STYLE_MAP.get(str(label or "").lower(), "primary")


def render_action_buttons(parent, specs, bg=None):
    """specs: (label, command) ou (label, command, style)."""
    bg = bg or parent.cget("bg")
    bar = tk.Frame(parent, bg=bg)
    bar.pack(side="left", fill="x", expand=True)
    for item in specs:
        if len(item) == 3:
            label, command, style = item
        else:
            label, command = item
            style = action_style(label)
        styled_button(bar, str(label).upper(), style=style, size="sm", command=command).pack(side="left", padx=2)
    return bar


def table_scroll_host(parent):
    """Area com scroll vertical; largura acompanha o painel (sem scroll horizontal)."""
    host = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground="#D3DAE3")
    host.pack(fill="both", expand=True)

    canvas = tk.Canvas(host, bg=COLORS["panel"], highlightthickness=0)
    vsb = tk.Scrollbar(host, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg=COLORS["panel"])
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _sync_scroll(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _sync_width(event):
        canvas.itemconfigure(window_id, width=event.width)

    def _wheel(event):
        bbox = canvas.bbox("all")
        if not bbox or bbox[3] - bbox[1] <= canvas.winfo_height():
            return "break"
        top, bottom = canvas.yview()
        delta = int(-1 * (event.delta / 120))
        if delta < 0 and top <= 0.001:
            canvas.yview_moveto(0)
            return "break"
        if delta > 0 and bottom >= 0.999:
            return "break"
        canvas.yview_scroll(delta, "units")
        return "break"

    inner.bind("<Configure>", _sync_scroll)
    canvas.bind("<Configure>", _sync_width)
    canvas.bind("<MouseWheel>", _wheel)
    inner.bind("<MouseWheel>", _wheel)
    return host, inner


def configure_treeview_columns(tree, columns, weights=None):
    """Treeview preenche a largura disponivel; sem scrollbar horizontal."""
    weights = weights or [1] * len(columns)
    for col, weight in zip(columns, weights):
        tree.heading(col, text=str(col).upper())
        tree.column(col, anchor="w", width=120, minwidth=70, stretch=bool(weight))


def grid_table_header(table, headers, weights, minsizes=None):
    minsizes = minsizes or [0] * len(headers)
    for index, (title, weight) in enumerate(zip(headers, weights)):
        table.grid_columnconfigure(index, weight=weight, minsize=minsizes[index] if index < len(minsizes) else 0)
        tk.Label(
            table,
            text=str(title).upper(),
            bg=COLORS["panel_alt"],
            fg=COLORS["muted"],
            font=("Segoe UI Semibold", 9),
            anchor="w",
            padx=8,
            pady=9,
        ).grid(row=0, column=index, sticky="ew")


def grid_table_cell(table, row, column, value, bg, *, truncate=None, fg=None, font=None):
    text = truncate_text(value, truncate) if truncate else value
    tk.Label(
        table,
        text=text,
        bg=bg,
        fg=fg or COLORS["text"],
        font=font or ("Segoe UI", 9),
        anchor="w",
        justify="left",
        padx=8,
        pady=10,
        wraplength=220 if truncate else 0,
    ).grid(row=row, column=column, sticky="ew")
