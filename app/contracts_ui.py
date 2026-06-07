"""Editor dos contratos exibidos no PDF de reserva."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext

from .components import panel_frame
from .contracts_model import CONTRACT_PROFILES, load_contract_text, reset_contract_texts, save_contract_texts
from .theme import COLORS, FONTS, badge_label, styled_button


def render_contract_cliente(parent, app):
    render_contract_editor(parent, app, "cliente")


def render_contract_motorista(parent, app):
    render_contract_editor(parent, app, "motorista")


def render_contract_editor(parent, app, profile):
    meta = CONTRACT_PROFILES[profile]
    accent = COLORS.get(meta["accent"], COLORS["primary"])
    accent_soft = COLORS.get(f'{meta["accent"]}_soft', COLORS["primary_soft"])

    parent.configure(bg=COLORS["bg"])

    header = panel_frame(parent)
    header.pack(fill="x", pady=(0, 12))
    tk.Frame(header, bg=accent, height=3).pack(fill="x")
    inner = tk.Frame(header, bg=COLORS["panel"])
    inner.pack(fill="x", padx=18, pady=16)

    title_row = tk.Frame(inner, bg=COLORS["panel"])
    title_row.pack(fill="x")
    title_box = tk.Frame(title_row, bg=COLORS["panel"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text=meta["title"], bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(title_box, text=meta["subtitle"], bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["small"]).pack(anchor="w", pady=(2, 0))

    actions = tk.Frame(title_row, bg=COLORS["panel"])
    actions.pack(side="right", anchor="n")
    badge_label(actions, meta["via_label"], tone=meta["accent"]).pack(side="left", padx=(0, 8))

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

    editors = {}

    def _section_card(title, hint, section_key):
        card = tk.Frame(body, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
        card.pack(fill="x", pady=(0, 12))
        head = tk.Frame(card, bg=accent_soft)
        head.pack(fill="x")
        tk.Label(head, text=title.upper(), bg=accent_soft, fg=accent, font=("Segoe UI Semibold", 10), padx=14, pady=10).pack(anchor="w")
        hint_label = tk.Label(card, text=hint, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"], wraplength=900, justify="left", padx=14, pady=10)
        hint_label.pack(anchor="w")
        text = scrolledtext.ScrolledText(
            card,
            height=10,
            bg=COLORS["input"],
            fg=COLORS["text"],
            relief="solid",
            bd=1,
            font=("Segoe UI", 10),
            wrap="word",
            padx=10,
            pady=8,
        )
        text.pack(fill="x", padx=14, pady=(0, 14))
        text.insert("1.0", load_contract_text(profile, section_key))
        editors[section_key] = text
        return text

    _section_card(
        "Clausulas do contrato",
        "Corpo principal do contrato (pagina 3 do PDF). Uma linha por paragrafo ou clausula.",
        "clausulas",
    )
    _section_card(
        "Politica de cancelamento",
        "Itens exibidos na secao POLITICA DE CANCELAMENTO (pagina 3 do PDF).",
        "cancelamento",
    )
    _section_card(
        "Clausulas adicionais",
        "Texto da pagina 4 do PDF, antes das assinaturas.",
        "adicionais",
    )

    footer = tk.Frame(body, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
    footer.pack(fill="x", pady=(0, 8))
    tk.Label(
        footer,
        text="Dica: alteracoes aqui afetam somente o PDF da via selecionada. Cliente e Motorista possuem textos independentes.",
        bg=COLORS["panel_alt"],
        fg=COLORS["muted"],
        font=FONTS["tiny"],
        wraplength=900,
        justify="left",
        padx=14,
        pady=12,
    ).pack(anchor="w")

    btn_row = tk.Frame(body, bg=COLORS["bg"])
    btn_row.pack(fill="x", pady=(0, 12))

    def _collect():
        return {key: widget.get("1.0", "end").strip() for key, widget in editors.items()}

    def _save():
        payload = _collect()
        if not payload.get("clausulas"):
            messagebox.showwarning("Contrato", "Informe ao menos uma clausula do contrato.", parent=app)
            return
        save_contract_texts(profile, payload)
        messagebox.showinfo("Contrato", f'{meta["title"]} salvo com sucesso.', parent=app)

    def _restore_defaults():
        if not messagebox.askyesno(
            "Restaurar padrao",
            f"Restaurar o texto padrao de {meta['title']}? As alteracoes nao salvas serao perdidas.",
            parent=app,
        ):
            return
        defaults = reset_contract_texts(profile)
        for key, widget in editors.items():
            widget.delete("1.0", "end")
            widget.insert("1.0", defaults[key])
        messagebox.showinfo("Contrato", "Texto padrao restaurado e salvo.", parent=app)

    styled_button(btn_row, "Salvar contrato", style="success", command=_save).pack(side="left", padx=(0, 8))
    styled_button(btn_row, "Restaurar padrao", style="secondary", command=_restore_defaults).pack(side="left")
