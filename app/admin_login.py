"""Login obrigatorio do administrador — UI desktop (Tkinter)."""
from __future__ import annotations

import secrets
import string
from pathlib import Path

from .admin_auth import authenticate_admin
from .branding import brand_display_name, brand_initials

_CAPTCHA_ALPHABET = string.ascii_letters + string.digits
_CAPTCHA_ALPHABET = "".join(ch for ch in _CAPTCHA_ALPHABET if ch not in "0O1lI")
_LOGIN_IMAGES = Path(__file__).resolve().parent / "master" / "static" / "master" / "images" / "login"


def _center_window(window, width, height):
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = max(0, (screen_w - width) // 2)
    y = max(0, (screen_h - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def _new_captcha_code(length: int = 6) -> str:
    return "".join(secrets.choice(_CAPTCHA_ALPHABET) for _ in range(length))


def _load_login_photo(path: Path, tk):
    if not path.is_file():
        return None
    try:
        return tk.PhotoImage(file=str(path))
    except tk.TclError:
        pass
    try:
        from PIL import Image, ImageTk

        image = Image.open(path)
        return ImageTk.PhotoImage(image)
    except Exception:
        return None


def _build_input(parent, label, *, show=None, tk=None, COLORS=None, FONTS=None):
    block = tk.Frame(parent, bg=COLORS["panel"])
    block.pack(fill="x", pady=(0, 12))
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

    from .theme import COLORS, FONTS, styled_button

    brand = brand_display_name()
    initials = brand_initials(brand)
    result = {"admin": None}
    captcha_state = {"code": _new_captcha_code()}

    root = tk.Tk()
    root.title("Acesso Administrativo")
    root.configure(bg=COLORS["white"])
    root.resizable(True, True)
    root.minsize(960, 620)
    _center_window(root, 1080, 680)

    shell = tk.Frame(root, bg=COLORS["white"])
    shell.pack(fill="both", expand=True)
    shell.grid_columnconfigure(0, weight=1, uniform="login")
    shell.grid_columnconfigure(1, weight=1, uniform="login")
    shell.grid_rowconfigure(0, weight=1)

    visual = tk.Frame(shell, bg="#111827")
    visual.grid(row=0, column=0, sticky="nsew")
    visual.grid_rowconfigure(0, weight=1)
    visual.grid_rowconfigure(1, weight=0)
    visual.grid_rowconfigure(2, weight=1)
    visual.grid_columnconfigure(0, weight=1)

    top_photo = _load_login_photo(_LOGIN_IMAGES / "hero-top.jpg", tk)
    bottom_photo = _load_login_photo(_LOGIN_IMAGES / "hero-bottom.jpg", tk)

    top_panel = tk.Label(visual, bg="#111827", image=top_photo) if top_photo else tk.Frame(visual, bg="#111827", height=180)
    top_panel.grid(row=0, column=0, sticky="nsew")
    if top_photo:
        top_panel.image = top_photo

    tagline = tk.Frame(visual, bg="#1f2937")
    tagline.grid(row=1, column=0, sticky="ew")
    tk.Label(
        tagline,
        text="Gerencie reservas, motoristas, clientes e operações em um único sistema moderno, rápido e inteligente.",
        bg="#1f2937",
        fg="#f9fafb",
        font=("Segoe UI", 11),
        wraplength=360,
        justify="center",
        padx=28,
        pady=24,
    ).pack()

    bottom_panel = tk.Label(visual, bg="#111827", image=bottom_photo) if bottom_photo else tk.Frame(visual, bg="#111827", height=180)
    bottom_panel.grid(row=2, column=0, sticky="nsew")
    if bottom_photo:
        bottom_panel.image = bottom_photo

    main = tk.Frame(shell, bg=COLORS["white"])
    main.grid(row=0, column=1, sticky="nsew")
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(0, weight=1)

    content = tk.Frame(main, bg=COLORS["white"])
    content.place(relx=0.5, rely=0.5, anchor="center", width=420)

    tk.Label(
        content,
        text=initials,
        bg=COLORS["primary_soft"],
        fg=COLORS["primary"],
        font=("Segoe UI Semibold", 8),
        padx=10,
        pady=4,
    ).pack()

    tk.Label(
        content,
        text=f"Painel {brand}",
        bg=COLORS["white"],
        fg=COLORS["text"],
        font=FONTS["title"],
    ).pack(pady=(10, 2))

    tk.Label(
        content,
        text="Acesse com segurança para gerir sua operação",
        bg=COLORS["white"],
        fg=COLORS["muted"],
        font=FONTS["subtitle"],
    ).pack(pady=(0, 18))

    card = tk.Frame(content, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    card.pack(fill="x")
    body = tk.Frame(card, bg=COLORS["panel"])
    body.pack(fill="both", expand=True, padx=22, pady=22)

    tk.Label(body, text="Faça seu login", bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["semibold_md"]).pack(anchor="w")
    tk.Label(
        body,
        text="Use seu usuário e senha para entrar no painel.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=FONTS["small"],
    ).pack(anchor="w", pady=(2, 14))

    email_entry = _build_input(body, "Usuário", tk=tk, COLORS=COLORS, FONTS=FONTS)
    password_entry = _build_input(body, "Senha", show="•", tk=tk, COLORS=COLORS, FONTS=FONTS)

    captcha_block = tk.Frame(body, bg=COLORS["panel"])
    captcha_block.pack(fill="x", pady=(0, 12))
    tk.Label(
        captcha_block,
        text="Código de segurança",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=FONTS["semibold_sm"],
    ).pack(anchor="w", pady=(0, 6))

    captcha_row = tk.Frame(captcha_block, bg=COLORS["panel"])
    captcha_row.pack(fill="x")
    captcha_label = tk.Label(
        captcha_row,
        text=captcha_state["code"],
        bg=COLORS["panel_alt"],
        fg=COLORS["text"],
        font=("Consolas", 14, "bold"),
        padx=12,
        pady=8,
        highlightthickness=1,
        highlightbackground=COLORS["line"],
    )
    captcha_label.pack(side="left", fill="x", expand=True)

    def refresh_captcha():
        captcha_state["code"] = _new_captcha_code()
        captcha_label.configure(text=captcha_state["code"])
        captcha_entry.delete(0, tk.END)

    styled_button(captcha_row, "↻", style="secondary", size="sm", command=refresh_captcha).pack(side="left", padx=(8, 0))
    captcha_entry = tk.Entry(
        captcha_block,
        font=FONTS["body"],
        bg=COLORS["input"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        relief="solid",
        bd=1,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["primary"],
    )
    captcha_entry.pack(fill="x", ipady=8, pady=(8, 0))

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
        captcha_value = captcha_entry.get().strip()
        if not email:
            show_error("Informe o usuário.")
            email_entry.focus_set()
            return
        if not password:
            show_error("Informe a senha.")
            password_entry.focus_set()
            return
        if captcha_value != captcha_state["code"]:
            show_error("Código de segurança inválido.")
            refresh_captcha()
            captcha_entry.focus_set()
            return
        admin_user, error = authenticate_admin(email, password)
        if not admin_user:
            show_error(error or "E-mail ou senha inválidos. Acesso restrito ao administrador.")
            password_entry.delete(0, tk.END)
            refresh_captcha()
            password_entry.focus_set()
            return
        result["admin"] = admin_user
        root.destroy()

    def on_close():
        result["admin"] = None
        root.destroy()

    styled_button(body, "→ Iniciar sessão", style="primary", size="lg", command=submit).pack(fill="x", pady=(4, 0))

    security = tk.Frame(content, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
    security.pack(fill="x", pady=(16, 0))
    security_body = tk.Frame(security, bg=COLORS["panel_alt"])
    security_body.pack(fill="x", padx=16, pady=14)
    tk.Label(security_body, text="Checkup de segurança", bg=COLORS["panel_alt"], fg=COLORS["text"], font=FONTS["semibold_sm"]).pack(anchor="w")
    for line in (
        "• Nunca compartilhe sua senha com terceiros.",
        "• Verifique o código de segurança antes de entrar.",
        "• Ative 2FA no menu Sistema > Configurações.",
    ):
        tk.Label(security_body, text=line, bg=COLORS["panel_alt"], fg=COLORS["muted"], font=FONTS["tiny"], anchor="w").pack(anchor="w", pady=(4, 0))

    tk.Label(content, text="© 2026 — Todos os direitos reservados.", bg=COLORS["white"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(pady=(14, 0))

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.bind("<Return>", submit)
    email_entry.focus_set()
    root.mainloop()
    return result["admin"]
