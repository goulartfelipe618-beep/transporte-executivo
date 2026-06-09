"""Alias de servico de sessao — compatibilidade com camada de dominio."""
from __future__ import annotations

from .auth_service import create_web_session, logout_admin, resolve_admin

__all__ = ["create_web_session", "logout_admin", "resolve_admin"]
