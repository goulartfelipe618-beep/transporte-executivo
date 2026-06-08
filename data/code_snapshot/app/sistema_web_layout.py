"""Layout HTML do painel web — espelha menu do desktop sem Tkinter."""
from __future__ import annotations

import html
from datetime import datetime

from .branding import brand_display_name, brand_initials
from .data import MENU_GROUPS, PAGE_TITLES
from .version import APP_BUILD

WEB_NAV = (
    {"type": "item", "key": "ABRANGENCIA", "label": "Abrangencia", "icon": "🗺️"},
    {"type": "item", "key": "AGENDA", "label": "Agenda", "icon": "📅"},
    {"type": "item", "key": "METRICAS", "label": "Metricas", "icon": "📊"},
    {"type": "group", "group": "FINANCEIRO"},
    {"type": "item", "key": "FIN_DASHBOARD", "label": "Dashboard", "group": "FINANCEIRO"},
    {"type": "item", "key": "FIN_LANCAMENTOS", "label": "Lancamentos", "group": "FINANCEIRO"},
    {"type": "item", "key": "FIN_CONTAS_PAGAR", "label": "Contas a pagar", "group": "FINANCEIRO"},
    {"type": "item", "key": "FIN_CONTAS_RECEBER", "label": "Contas a receber", "group": "FINANCEIRO"},
    {"type": "item", "key": "FIN_RELATORIOS", "label": "Relatorios", "group": "FINANCEIRO"},
    {"type": "group", "group": "TRANSFER"},
    {"type": "item", "key": "SOLICITACOES", "label": "Solicitacoes", "group": "TRANSFER"},
    {"type": "item", "key": "RESERVAS", "label": "Reservas", "group": "TRANSFER"},
    {"type": "item", "key": "MOTORISTAS", "label": "Motoristas", "icon": "👤"},
    {"type": "item", "key": "CLIENTES", "label": "Empresas", "icon": "🏢"},
    {"type": "item", "key": "VEICULOS", "label": "Veiculos", "icon": "🚗"},
    {"type": "group", "group": "REDE"},
    {"type": "item", "key": "REDE", "label": "Cadastro rede", "group": "REDE"},
    {"type": "item", "key": "REDE_SOLICITACOES", "label": "Solicitacoes rede", "group": "REDE"},
    {"type": "item", "key": "REDE_DASHBOARD", "label": "Dashboard rede", "group": "REDE"},
    {"type": "group", "group": "SISTEMA"},
    {"type": "item", "key": "CONFIGURACOES", "label": "Configuracoes", "group": "SISTEMA"},
    {"type": "item", "key": "AUTOMACOES", "label": "Automacoes", "group": "SISTEMA"},
)

VALID_MODULE_KEYS = frozenset(PAGE_TITLES)

GROUP_LABELS = {
    "FINANCEIRO": MENU_GROUPS["FINANCEIRO"],
    "TRANSFER": MENU_GROUPS["TRANSFER"],
    "REDE": MENU_GROUPS["REDE"],
    "SISTEMA": MENU_GROUPS["SISTEMA"],
}


def esc(value):
    return html.escape(str(value if value is not None else ""))


def module_href(key):
    return f"/painel/{key.lower()}"


def _sidebar_nav(active_key):
    parts = []
    for item in WEB_NAV:
        if item["type"] == "group":
            group = item["group"]
            label, icon = GROUP_LABELS.get(group, (group, ""))
            parts.append(f'<div class="nav-group">{esc(icon)} {esc(label.upper())}</div>')
            continue
        key = item["key"]
        group = item.get("group")
        cls = "nav-link active" if key == active_key else "nav-link"
        sub = " nav-sub" if group else ""
        icon = item.get("icon", "")
        icon_html = f'<span class="nav-icon">{esc(icon)}</span>' if icon else ""
        text = esc(item.get("label", PAGE_TITLES.get(key, key)).upper())
        parts.append(f'<a href="{module_href(key)}" class="{cls}{sub}">{icon_html}<span>{text}</span></a>')
    return "\n".join(parts)


def panel_page(admin, active_key, content_html, *, brand_name=None):
    brand_name = brand_name or brand_display_name()
    initials = brand_initials(brand_name)
    admin_name = esc(admin.get("nome") or "Administrador")
    admin_email = esc(admin.get("email") or "")
    title = esc(PAGE_TITLES.get(active_key, active_key))
    today = datetime.now().strftime("%d/%m/%Y")
    nav = _sidebar_nav(active_key)
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title} — {esc(brand_name)}</title>
<style>
:root{{--bg:#f0f4f8;--panel:#fff;--sidebar:#1a2332;--sidebar-soft:#243044;--sidebar-hover:#2d3b52;--sidebar-active:#2563eb;--text:#0f172a;--muted:#64748b;--line:#e2e8f0;--primary:#2563eb;--success:#16a34a;--warn:#d97706;--danger:#dc2626}}
*{{box-sizing:border-box}}body{{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:var(--bg);color:var(--text)}}
.app{{display:grid;grid-template-columns:260px 1fr;min-height:100vh}}
.sidebar{{background:var(--sidebar);color:#cbd5e1;display:flex;flex-direction:column}}
.brand{{padding:18px 16px;border-bottom:1px solid var(--sidebar-soft)}}
.brand-row{{display:flex;align-items:center;gap:10px}}
.brand-badge{{width:36px;height:36px;border-radius:8px;background:var(--sidebar-active);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem}}
.brand-title{{font-weight:700;color:#fff;font-size:.95rem;line-height:1.2}}
.brand-sub{{font-size:.68rem;color:#94a3b8;letter-spacing:.04em}}
.nav{{flex:1;overflow:auto;padding:10px 8px 16px}}
.nav-group{{padding:10px 12px 4px;font-size:.68rem;font-weight:700;color:#94a3b8;letter-spacing:.06em}}
.nav-link{{display:flex;align-items:center;gap:8px;padding:9px 12px;margin:2px 0;border-radius:8px;color:#cbd5e1;text-decoration:none;font-size:.82rem}}
.nav-link:hover{{background:var(--sidebar-hover);color:#fff}}
.nav-link.active{{background:var(--sidebar-active);color:#fff;font-weight:600}}
.nav-sub{{padding-left:22px;font-size:.78rem}}
.nav-icon{{width:18px;text-align:center}}
.sidebar-foot{{padding:12px 16px;border-top:1px solid var(--sidebar-soft);font-size:.72rem;color:#94a3b8}}
.main{{display:flex;flex-direction:column;min-width:0}}
.topbar{{display:flex;align-items:center;justify-content:space-between;padding:0 20px;min-height:62px;background:var(--panel);border-bottom:1px solid var(--line)}}
.topbar h1{{margin:0;font-size:1.15rem}}
.topbar-meta{{display:flex;align-items:center;gap:10px;color:var(--muted);font-size:.82rem}}
.badge{{padding:4px 10px;border-radius:999px;background:#eff6ff;color:var(--primary);font-size:.72rem;font-weight:600}}
.btn{{border:0;border-radius:8px;padding:8px 14px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}}
.btn-danger{{background:var(--danger);color:#fff}}
.content{{padding:18px 20px 28px;overflow:auto}}
.cards{{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));margin-bottom:18px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}}
.card .label{{color:var(--muted);font-size:.78rem}}
.card .value{{font-size:1.45rem;font-weight:700;margin-top:4px}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-bottom:16px}}
.panel-head{{padding:14px 16px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}
.panel-head h2{{margin:0;font-size:1rem}}
.panel-head p{{margin:4px 0 0;color:var(--muted);font-size:.85rem}}
.table-wrap{{overflow:auto}}
table{{width:100%;border-collapse:collapse;font-size:.84rem}}
th,td{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th{{background:#f8fafc;color:var(--muted);font-size:.74rem;text-transform:uppercase;letter-spacing:.04em}}
tr:hover td{{background:#f8fafc}}
.empty{{padding:28px;text-align:center;color:var(--muted)}}
.note{{padding:12px 14px;border-radius:10px;background:#fffbeb;border:1px solid #fde68a;color:#92400e;font-size:.84rem;margin-bottom:14px}}
.pill{{display:inline-block;padding:3px 8px;border-radius:999px;font-size:.72rem;font-weight:600;background:#eff6ff;color:var(--primary)}}
.pill.ok{{background:#ecfdf5;color:var(--success)}}
.pill.warn{{background:#fff7ed;color:var(--warn)}}
.pill.bad{{background:#fef2f2;color:var(--danger)}}
@media(max-width:960px){{.app{{grid-template-columns:1fr}}.sidebar{{display:none}}}}
</style></head><body>
<div class="app">
<aside class="sidebar">
<div class="brand"><div class="brand-row"><div class="brand-badge">{esc(initials)}</div><div><div class="brand-title">{esc(brand_name.upper())}</div><div class="brand-sub">PAINEL OPERACIONAL WEB</div></div></div></div>
<nav class="nav">{nav}</nav>
<div class="sidebar-foot">● ONLINE · BUILD {APP_BUILD}</div>
</aside>
<main class="main">
<header class="topbar">
<h1>{title}</h1>
<div class="topbar-meta">
<span class="badge">Build {APP_BUILD}</span>
<span>{today}</span>
<span>{admin_name}</span>
<form method="post" action="/logout" style="margin:0"><button type="submit" class="btn btn-danger">Sair</button></form>
</div>
</header>
<section class="content">{content_html}</section>
</main>
</div>
</body></html>"""
