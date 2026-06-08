"""Autenticacao do administrador master — sem dependencia de Tkinter (headless/web)."""
from __future__ import annotations

from .repository.supabase_client import call_rpc, is_configured


def authenticate_admin(email, password):
    if not is_configured():
        return None, "Supabase nao configurado. Verifique data/supabase_credentials.json."
    try:
        result = call_rpc(
            "master_admin_login",
            {"p_email": str(email or "").strip(), "p_password": str(password or "")},
        )
    except RuntimeError as exc:
        return None, f"Falha ao validar login: {exc}"
    if not result or not result.get("ok"):
        return None, (result or {}).get("error") or "E-mail ou senha invalidos."
    admin = dict((result.get("admin") or {}))
    if not admin.get("email"):
        return None, "Resposta de login invalida."
    return {
        "id": admin.get("id", ""),
        "email": admin.get("email", ""),
        "nome": admin.get("nome") or "Administrador",
        "perfil": admin.get("perfil") or "Administrador Master",
    }, ""
