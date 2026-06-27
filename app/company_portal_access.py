"""Token de primeiro acesso ao portal corporativo (uso unico)."""
from __future__ import annotations

import secrets
from datetime import datetime

from .company_model import append_portal_activity


def _timestamp() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def generate_first_access_token() -> str:
    return secrets.token_urlsafe(24)


def mask_first_access_token(token: str) -> str:
    raw = str(token or "").strip()
    if not raw:
        return "—"
    if len(raw) <= 10:
        return "•" * len(raw)
    visible = 4
    hidden = max(4, len(raw) - (visible * 2))
    return f"{raw[:visible]}{'•' * hidden}{raw[-visible:]}"


def first_access_pending(company) -> bool:
    if not company:
        return False
    if company.get("portal_first_access_consumed_em"):
        return False
    return bool(str(company.get("portal_first_access_token", "")).strip())


def first_access_token_valid(company, token) -> bool:
    if not first_access_pending(company):
        return True
    expected = str(company.get("portal_first_access_token", "")).strip()
    supplied = str(token or "").strip()
    if not expected or not supplied:
        return False
    return secrets.compare_digest(expected, supplied)


def consume_first_access_token(app, company, *, ip: str = "") -> bool:
    if not company or not first_access_pending(company):
        return False
    company["portal_first_access_consumed_em"] = _timestamp()
    append_portal_activity(
        company,
        "Primeiro acesso",
        f"Token de primeiro acesso consumido{f' ({ip})' if ip else ''}.",
    )
    if hasattr(app, "save_state"):
        app.save_state()
    return True


def first_access_denied_html(company_name: str = "Empresa") -> str:
    name = str(company_name or "Empresa").strip()
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><title>Acesso restrito</title>
<style>body{{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0;padding:24px}}
.card{{max-width:480px;background:#fff;color:#1e293b;border-radius:12px;padding:28px;box-shadow:0 20px 50px rgba(0,0,0,.35)}}
h1{{margin:0 0 8px;font-size:1.25rem}}p{{margin:0;color:#64748b;line-height:1.5}}</style></head>
<body><div class="card"><h1>Primeiro acesso — {name}</h1>
<p>Este portal so pode ser aberto na primeira vez usando o <strong>link completo com token</strong> enviado pelo administrador.</p>
<p style="margin-top:12px">Solicite o link oficial ao suporte da operacao.</p></div></body></html>"""
