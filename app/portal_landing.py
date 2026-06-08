"""Paginas HTML simples na raiz dos portais web."""
from __future__ import annotations

from .portal_urls import company_portal_base, driver_portal_base
from .version import APP_BUILD


def _page(title, subtitle, body_html):
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
body{{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:#f0f4f8;color:#0f172a}}
.wrap{{max-width:720px;margin:48px auto;padding:24px}}.card{{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:28px}}
h1{{margin:0 0 8px;font-size:1.6rem;color:#2563eb}}.muted{{color:#64748b;line-height:1.5}}code{{background:#eff6ff;padding:2px 6px;border-radius:6px}}
</style></head><body><div class="wrap"><div class="card">
<h1>{title}</h1>
<p class="muted">{subtitle}</p>
{body_html}
<p class="muted" style="margin-top:20px;font-size:.8rem">Build {APP_BUILD}</p>
</div></div></body></html>"""


def driver_portal_landing():
    base = driver_portal_base()
    return _page(
        "Portal do Motorista",
        "Acesse com o link personalizado enviado pelo administrador.",
        f"<p class='muted'>Formato do link:<br><code>{base}/driver/{{seu-slug}}</code></p>",
    )


def company_portal_landing():
    base = company_portal_base()
    return _page(
        "Portal da Empresa",
        "Acesse com o link exclusivo da sua empresa contratante.",
        f"<p class='muted'>Formatos aceitos:<br><code>{base}/empresa/{{slug}}</code><br><code>{base}/emp-0001/{{codigo}}</code></p>",
    )
