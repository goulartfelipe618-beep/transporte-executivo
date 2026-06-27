"""Login obrigatorio do administrador — UI desktop (Tkinter)."""
from __future__ import annotations

import secrets
import string
from pathlib import Path

from .admin_auth import authenticate_admin
from .branding import brand_display_name

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
        path = None
    try:
        from app.cdn.urls import cdn_enabled, static_url

        if cdn_enabled() and path is not None:
            import httpx
            from io import BytesIO
            from PIL import Image, ImageTk

            url = static_url(f"master/images/login/{path.name}")
            response = httpx.get(url, timeout=20.0, follow_redirects=True)
            response.raise_for_status()
            return ImageTk.PhotoImage(Image.open(BytesIO(response.content)))
    except Exception:
        pass
    if path and path.is_file():
        try:
            return tk.PhotoImage(file=str(path))
        except tk.TclError:
            pass
        try:
            from PIL import Image, ImageTk

            return ImageTk.PhotoImage(Image.open(path))
        except Exception:
            return None
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
    result = {"admin": None}
    captcha_state = {"code": _new_captcha_code()}
    panel_bg = "#ffffff"

    root = tk.Tk()
    root.title("Login")
    root.configure(bg="#0f172a")
    root.resizable(True, True)
    root.minsize(900, 600)
    _center_window(root, 1100, 720)

    canvas = tk.Canvas(root, highlightthickness=0, bd=0, bg="#0f172a")
    canvas.pack(fill="both", expand=True)
    bg_holder = {"photo": None}

    def _draw_background(_event=None):
        width = max(root.winfo_width(), 900)
        height = max(root.winfo_height(), 600)
        photo = _load_login_photo(_LOGIN_IMAGES / "login-background.jpg", tk)
        if photo is None:
            canvas.delete("bg")
            canvas.create_rectangle(0, 0, width, height, fill="#0f172a", outline="", tags="bg")
            return
        try:
            from PIL import Image, ImageTk

            path = _LOGIN_IMAGES / "login-background.jpg"
            if path.is_file():
                image = Image.open(path).resize((width, height), Image.Resampling.LANCZOS)
                bg_holder["photo"] = ImageTk.PhotoImage(image)
                canvas.delete("bg")
                canvas.create_image(0, 0, anchor="nw", image=bg_holder["photo"], tags="bg")
        except Exception:
            canvas.delete("bg")
            canvas.create_rectangle(0, 0, width, height, fill="#0f172a", outline="", tags="bg")

    panel = tk.Frame(canvas, bg=panel_bg, highlightthickness=0)
    panel_window = canvas.create_window(0, 0, window=panel, anchor="center", tags="panel")

    def _layout(_event=None):
        width = max(root.winfo_width(), 900)
        height = max(root.winfo_height(), 600)
        canvas.coords(panel_window, width // 2, height // 2)
        _draw_background()

    root.bind("<Configure>", _layout)

    content = tk.Frame(panel, bg=panel_bg)
    content.pack(padx=34, pady=32)

    tk.Label(content, text="Login", bg=panel_bg, fg="#374151", font=("Segoe UI Semibold", 22)).pack()
    tk.Label(content, text=brand, bg=panel_bg, fg="#6b7280", font=("Segoe UI", 10)).pack(pady=(2, 22))

    email_entry = _build_input(content, "E-mail", tk=tk, COLORS={**COLORS, "panel": panel_bg}, FONTS=FONTS)
    password_entry = _build_input(content, "Senha", show="•", tk=tk, COLORS={**COLORS, "panel": panel_bg}, FONTS=FONTS)

    captcha_block = tk.Frame(content, bg=panel_bg)
    captcha_block.pack(fill="x", pady=(0, 12))
    tk.Label(captcha_block, text="Código de segurança", bg=panel_bg, fg=COLORS["text"], font=FONTS["semibold_sm"]).pack(anchor="w", pady=(0, 6))
    captcha_row = tk.Frame(captcha_block, bg=panel_bg)
    captcha_row.pack(fill="x")
    captcha_label = tk.Label(
        captcha_row,
        text=captcha_state["code"],
        bg="#f9fafb",
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

    forgot = tk.Frame(content, bg=panel_bg)
    forgot.pack(fill="x", pady=(2, 14))
    tk.Label(forgot, text="Esqueceu a senha?", bg=panel_bg, fg=COLORS["primary"], font=("Segoe UI", 9, "underline"), cursor="hand2").pack(anchor="e")

    error_label = tk.Label(content, text="", bg=COLORS["danger_soft"], fg=COLORS["danger"], font=FONTS["small"], padx=10, pady=8, wraplength=340, justify="left")

    def hide_error():
        error_label.pack_forget()
        error_label.configure(text="")

    def show_error(message):
        error_label.configure(text=message)
        error_label.pack(fill="x", pady=(0, 10))

    def submit(_event=None):
        hide_error()
        email = email_entry.get().strip()
        password = password_entry.get()
        captcha_value = captcha_entry.get().strip()
        if not email:
            show_error("Informe o e-mail.")
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
            show_error(error or "E-mail ou senha inválidos.")
            password_entry.delete(0, tk.END)
            refresh_captcha()
            password_entry.focus_set()
            return
        from .totp_ui import require_totp_access_gate

        if not require_totp_access_gate(root):
            show_error("Autenticacao em 2 fatores obrigatoria para acessar o sistema.")
            password_entry.delete(0, tk.END)
            refresh_captcha()
            password_entry.focus_set()
            return
        result["admin"] = admin_user
        root.destroy()

    def on_close():
        result["admin"] = None
        root.destroy()

    styled_button(content, "Enviar", style="outline_primary", size="lg", command=submit).pack(pady=(0, 8))
    tk.Label(content, text="Nunca compartilhe sua senha.", bg=panel_bg, fg="#9ca3af", font=FONTS["tiny"]).pack(pady=(8, 0))

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.bind("<Return>", submit)
    root.update_idletasks()
    _layout()
    email_entry.focus_set()
    root.mainloop()
    return result["admin"]
