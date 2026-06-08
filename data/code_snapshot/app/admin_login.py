"""Login obrigatorio do administrador — UI desktop (Tkinter)."""
from __future__ import annotations

from .admin_auth import authenticate_admin


def _center_window(window, width, height):
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = max(0, (screen_w - width) // 2)
    y = max(0, (screen_h - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def _build_input(parent, label, *, show=None, tk=None, COLORS=None, FONTS=None):
    block = tk.Frame(parent, bg=COLORS["panel"])
    block.pack(fill="x", pady=(0, 14))
    tk.Label(
        block,
        text=label,
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=FONTS["semibold_sm"],
    ).pack(anchor="w", pady=(0, 6))
    entry = tk.Entry(
        block,
        font=FONTS["body"],
        bg=COLORS["input"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        relief="solid",
        bd=1,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["primary"],
        show=show,
    )
    entry.pack(fill="x", ipady=8)
    return entry


def require_admin_login():
    """Exibe tela de login modal. Retorna dict do admin ou None se cancelado."""
    import tkinter as tk

    from .theme import COLORS, FONTS, panel_frame, styled_button

    result = {"admin": None}

    root = tk.Tk()
    root.title("Acesso Administrativo")
    root.configure(bg=COLORS["sidebar"])
    root.resizable(False, False)
    _center_window(root, 460, 560)

    shell = tk.Frame(root, bg=COLORS["sidebar"])
    shell.pack(fill="both", expand=True, padx=28, pady=28)

    card = panel_frame(shell, bg=COLORS["panel"])
    card.pack(fill="both", expand=True)

    header = tk.Frame(card, bg=COLORS["primary"], height=6)
    header.pack(fill="x")

    body = tk.Frame(card, bg=COLORS["panel"])
    body.pack(fill="both", expand=True, padx=28, pady=28)

    logo = tk.Label(
        body,
        text="NT",
        bg=COLORS["primary_soft"],
        fg=COLORS["primary"],
        font=("Segoe UI Semibold", 18),
        width=3,
        height=1,
        padx=4,
        pady=6,
    )
    logo.pack(anchor="w")

    tk.Label(
        body,
        text="Central Operacional Master",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=FONTS["title"],
    ).pack(anchor="w", pady=(14, 4))

    tk.Label(
        body,
        text="Identifique-se para acessar o painel administrativo.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=FONTS["subtitle"],
        wraplength=340,
        justify="left",
    ).pack(anchor="w", pady=(0, 22))

    email_entry = _build_input(body, "E-mail administrativo", tk=tk, COLORS=COLORS, FONTS=FONTS)
    password_entry = _build_input(body, "Senha", show="•", tk=tk, COLORS=COLORS, FONTS=FONTS)

    error_label = tk.Label(
        body,
        text="",
        bg=COLORS["danger_soft"],
        fg=COLORS["danger"],
        font=FONTS["small"],
        padx=10,
        pady=8,
        wraplength=340,
        justify="left",
    )

    def hide_error():
        error_label.pack_forget()
        error_label.configure(text="")

    def show_error(message):
        error_label.configure(text=message)
        error_label.pack(fill="x", pady=(0, 12))

    def submit(_event=None):
        hide_error()
        email = email_entry.get().strip()
        password = password_entry.get()
        if not email:
            show_error("Informe o e-mail administrativo.")
            email_entry.focus_set()
            return
        if not password:
            show_error("Informe a senha.")
            password_entry.focus_set()
            return
        admin_user, error = authenticate_admin(email, password)
        if not admin_user:
            show_error(error or "E-mail ou senha invalidos. Acesso restrito ao administrador.")
            password_entry.delete(0, tk.END)
            password_entry.focus_set()
            return
        result["admin"] = admin_user
        root.destroy()

    def on_close():
        result["admin"] = None
        root.destroy()

    actions = tk.Frame(body, bg=COLORS["panel"])
    actions.pack(fill="x", pady=(6, 0))
    styled_button(actions, "Entrar no sistema", style="primary", size="lg", command=submit).pack(fill="x")

    tk.Label(
        body,
        text="Acesso validado no Supabase (master_admins).",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=FONTS["tiny"],
    ).pack(anchor="w", pady=(16, 0))

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.bind("<Return>", submit)
    email_entry.focus_set()
    root.mainloop()
    return result["admin"]
