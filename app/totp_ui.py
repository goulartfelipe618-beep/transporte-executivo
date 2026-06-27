"""Dialogo Tkinter para configurar 2FA (TOTP) no painel desktop."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from .totp_auth import (
    TOTP_ISSUER,
    disable_totp,
    enable_totp,
    generate_totp_secret,
    is_totp_enabled,
    provisioning_uri,
    totp_status,
)
from .theme import COLORS, FONTS, styled_button


def open_totp_settings_dialog(app):
    from .settings_store import load_settings

    settings = load_settings()
    status = totp_status(settings)
    win = tk.Toplevel(app)
    win.title("Autenticacao em 2 fatores (2FA)")
    win.configure(bg=COLORS["bg"])
    win.transient(app)
    win.grab_set()
    win.geometry("520x560")
    win.minsize(480, 420)

    body = tk.Frame(win, bg=COLORS["bg"], padx=18, pady=16)
    body.pack(fill="both", expand=True)

    tk.Label(
        body,
        text="Seguranca — 2FA (TOTP)",
        bg=COLORS["bg"],
        fg=COLORS["text"],
        font=FONTS["title"],
    ).pack(anchor="w")
    tk.Label(
        body,
        text="Use Google Authenticator, Authentik ou app compativel com TOTP.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=460,
        justify="left",
    ).pack(anchor="w", pady=(4, 12))

    state = {"secret": "", "photo": None}
    qr_label = tk.Label(body, bg=COLORS["bg"])
    qr_label.pack(pady=(0, 8))

    secret_var = tk.StringVar(value="")
    secret_entry = tk.Entry(body, textvariable=secret_var, font=("Consolas", 10), state="readonly")
    secret_entry.pack(fill="x", pady=(0, 8))

    code_var = tk.StringVar()
    code_row = tk.Frame(body, bg=COLORS["bg"])
    code_row.pack(fill="x", pady=(0, 8))
    tk.Label(code_row, text="Codigo de 6 digitos", bg=COLORS["bg"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w")
    tk.Entry(code_row, textvariable=code_var, font=("Segoe UI", 12), justify="center").pack(fill="x", ipady=6, pady=(4, 0))

    msg = tk.Label(body, text="", bg=COLORS["bg"], fg=COLORS["danger"], font=FONTS["small"], wraplength=460, justify="left")
    msg.pack(anchor="w", pady=(4, 8))

    actions = tk.Frame(body, bg=COLORS["bg"])
    actions.pack(fill="x", pady=(8, 0))

    def _render_qr(secret: str):
        account = status["account"]
        uri = provisioning_uri(secret, account)
        try:
            import qrcode
            from PIL import Image, ImageTk

            img = qrcode.make(uri)
            img = img.resize((220, 220))
            state["photo"] = ImageTk.PhotoImage(img)
            qr_label.configure(image=state["photo"])
        except Exception:
            qr_label.configure(image="", text="QR indisponivel — use o codigo manual abaixo.")
        secret_var.set(secret)

    def _start_setup():
        msg.configure(text="", fg=COLORS["danger"])
        secret = generate_totp_secret()
        state["secret"] = secret
        _render_qr(secret)
        msg.configure(text="Escaneie o QR ou copie o codigo manual. Depois informe o codigo de 6 digitos.", fg=COLORS["muted"])

    def _confirm_enable():
        secret = state["secret"] or secret_var.get().strip()
        code = code_var.get().strip()
        ok, err = enable_totp(secret, code, account_email=status["account"])
        if not ok:
            msg.configure(text=err, fg=COLORS["danger"])
            return
        messagebox.showinfo("2FA", "Autenticacao em dois fatores ativada com sucesso.", parent=win)
        win.destroy()

    def _confirm_disable():
        code = code_var.get().strip()
        ok, err = disable_totp(code)
        if not ok:
            msg.configure(text=err, fg=COLORS["danger"])
            return
        messagebox.showinfo("2FA", "Autenticacao em dois fatores desativada.", parent=win)
        win.destroy()

    if status["enabled"]:
        tk.Label(
            body,
            text=f"2FA ativo desde {status['enabled_em'] or '—'}",
            bg=COLORS["success_soft"],
            fg=COLORS["success"],
            font=("Segoe UI Semibold", 10),
            padx=12,
            pady=10,
        ).pack(fill="x", pady=(0, 12))
        tk.Label(
            body,
            text="Para desativar, informe o codigo atual do autenticador.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=FONTS["small"],
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        styled_button(actions, "Desativar 2FA", style="danger", command=_confirm_disable).pack(side="left")
    else:
        tk.Label(
            body,
            text="2FA desativado. Acoes sensiveis (ex.: excluir empresa) exigem 2FA ativo.",
            bg=COLORS["warning_soft"],
            fg=COLORS["warning"],
            font=FONTS["small"],
            padx=12,
            pady=10,
            wraplength=460,
            justify="left",
        ).pack(fill="x", pady=(0, 12))
        styled_button(actions, "Gerar QR Code", style="primary", command=_start_setup).pack(side="left", padx=(0, 8))
        styled_button(actions, "Ativar 2FA", style="success", command=_confirm_enable).pack(side="left")

    styled_button(actions, "Fechar", style="secondary", command=win.destroy).pack(side="right")


def require_totp_access_gate(parent) -> bool:
    """Exige 2FA configurado e codigo valido antes de liberar o sistema desktop."""
    if not is_totp_enabled():
        return _mandatory_totp_setup_dialog(parent)
    return _verify_totp_dialog(parent)


def _verify_totp_dialog(parent) -> bool:
    from .totp_auth import verify_action_totp

    result = {"ok": False}
    win = tk.Toplevel(parent)
    win.title("Verificacao 2FA")
    win.configure(bg=COLORS["bg"])
    win.transient(parent)
    win.grab_set()
    win.geometry("420x280")
    win.protocol("WM_DELETE_WINDOW", lambda: win.destroy())

    body = tk.Frame(win, bg=COLORS["bg"], padx=18, pady=16)
    body.pack(fill="both", expand=True)
    tk.Label(body, text="Codigo 2FA", bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(
        body,
        text="Informe o codigo de 6 digitos do autenticador para entrar.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=360,
        justify="left",
    ).pack(anchor="w", pady=(4, 12))

    code_var = tk.StringVar()
    tk.Entry(body, textvariable=code_var, font=("Segoe UI", 14), justify="center").pack(fill="x", ipady=8)
    msg = tk.Label(body, text="", bg=COLORS["bg"], fg=COLORS["danger"], font=FONTS["small"], wraplength=360, justify="left")
    msg.pack(anchor="w", pady=(8, 0))

    def submit(_event=None):
        ok, err = verify_action_totp(code_var.get().strip())
        if not ok:
            msg.configure(text=err)
            return
        result["ok"] = True
        win.destroy()

    actions = tk.Frame(body, bg=COLORS["bg"])
    actions.pack(fill="x", pady=(16, 0))
    styled_button(actions, "Entrar", style="success", command=submit).pack(side="left")
    styled_button(actions, "Cancelar", style="secondary", command=win.destroy).pack(side="right")
    win.bind("<Return>", submit)
    code_var.trace_add("write", lambda *_: msg.configure(text=""))
    win.wait_window()
    return result["ok"]


def _mandatory_totp_setup_dialog(parent) -> bool:
    result = {"ok": False}
    settings = __import__("app.settings_store", fromlist=["load_settings"]).load_settings()
    status = totp_status(settings)
    win = tk.Toplevel(parent)
    win.title("2FA obrigatorio")
    win.configure(bg=COLORS["bg"])
    win.transient(parent)
    win.grab_set()
    win.geometry("520x600")
    win.protocol("WM_DELETE_WINDOW", lambda: win.destroy())

    body = tk.Frame(win, bg=COLORS["bg"], padx=18, pady=16)
    body.pack(fill="both", expand=True)
    tk.Label(body, text="Configure o 2FA para continuar", bg=COLORS["warning_soft"], fg=COLORS["warning"], font=("Segoe UI Semibold", 10), padx=12, pady=10, wraplength=460, justify="left").pack(fill="x", pady=(0, 12))
    tk.Label(body, text="O acesso ao sistema so e liberado apos ativar autenticacao em dois fatores.", bg=COLORS["bg"], fg=COLORS["muted"], font=FONTS["small"], wraplength=460, justify="left").pack(anchor="w", pady=(0, 12))

    state = {"secret": "", "photo": None}
    qr_label = tk.Label(body, bg=COLORS["bg"])
    qr_label.pack(pady=(0, 8))
    secret_var = tk.StringVar(value="")
    tk.Entry(body, textvariable=secret_var, font=("Consolas", 10), state="readonly").pack(fill="x", pady=(0, 8))
    code_var = tk.StringVar()
    tk.Label(body, text="Codigo de 6 digitos", bg=COLORS["bg"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w")
    tk.Entry(body, textvariable=code_var, font=("Segoe UI", 12), justify="center").pack(fill="x", ipady=6, pady=(4, 8))
    msg = tk.Label(body, text="", bg=COLORS["bg"], fg=COLORS["danger"], font=FONTS["small"], wraplength=460, justify="left")
    msg.pack(anchor="w")

    def _render_qr(secret: str):
        uri = provisioning_uri(secret, status["account"])
        try:
            import qrcode
            from PIL import Image, ImageTk

            img = qrcode.make(uri).resize((200, 200))
            state["photo"] = ImageTk.PhotoImage(img)
            qr_label.configure(image=state["photo"])
        except Exception:
            qr_label.configure(text="Use o codigo manual abaixo.")
        secret_var.set(secret)

    def _start_setup():
        secret = generate_totp_secret()
        state["secret"] = secret
        _render_qr(secret)
        msg.configure(text="Escaneie o QR e informe o codigo.", fg=COLORS["muted"])

    def _confirm_enable():
        secret = state["secret"] or secret_var.get().strip()
        ok, err = enable_totp(secret, code_var.get().strip(), account_email=status["account"])
        if not ok:
            msg.configure(text=err, fg=COLORS["danger"])
            return
        result["ok"] = True
        win.destroy()

    actions = tk.Frame(body, bg=COLORS["bg"])
    actions.pack(fill="x", pady=(12, 0))
    styled_button(actions, "Gerar QR Code", style="primary", command=_start_setup).pack(side="left", padx=(0, 8))
    styled_button(actions, "Ativar e entrar", style="success", command=_confirm_enable).pack(side="left")
    styled_button(actions, "Cancelar", style="secondary", command=win.destroy).pack(side="right")
    win.wait_window()
    return result["ok"] and is_totp_enabled()
