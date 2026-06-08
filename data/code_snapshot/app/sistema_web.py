"""Painel web do Sistema Master — sistema.transporteexecutivo.com (mesmo login admin)."""
from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .admin_login import authenticate_admin
from .bind_host import bind_host
from .portal_urls import api_base_url, company_portal_base, driver_portal_base, engine_base, sistema_web_base
from .version import APP_BUILD

SISTEMA_WEB_PORT = 8772
_SESSIONS = {}


def _new_session(admin):
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = dict(admin or {})
    return token


def _get_session(token):
    return _SESSIONS.get(str(token or "").strip())


def _revoke_session(token):
    _SESSIONS.pop(str(token or "").strip(), None)


def _html_page(body, *, title="Sistema Master"):
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
:root{{--bg:#0f172a;--panel:#fff;--primary:#2563eb;--text:#0f172a;--muted:#64748b;--line:#e2e8f0}}
*{{box-sizing:border-box}}body{{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:linear-gradient(160deg,#0f172a,#1e293b);color:var(--text);min-height:100vh}}
.wrap{{max-width:980px;margin:0 auto;padding:24px}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:24px;box-shadow:0 12px 40px rgba(15,23,42,.25)}}
h1{{margin:0 0 8px;font-size:1.5rem}}.muted{{color:var(--muted);font-size:.9rem}}label{{display:block;font-size:.82rem;font-weight:600;margin:12px 0 6px}}
input{{width:100%;padding:11px;border:1px solid var(--line);border-radius:10px}}button{{margin-top:16px;padding:11px 16px;border:0;border-radius:10px;background:var(--primary);color:#fff;font-weight:600;cursor:pointer}}
.error{{color:#dc2626;font-size:.85rem;margin-top:10px}}.grid{{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));margin-top:18px}}
.tile{{border:1px solid var(--line);border-radius:12px;padding:16px;background:#f8fafc}}.tile b{{display:block;margin-bottom:6px;color:var(--primary)}}
.top{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}a{{color:var(--primary);text-decoration:none;font-weight:600}}
</style></head><body><div class="wrap">{body}</div></body></html>"""


def _login_html(error=""):
    err = f'<p class="error">{error}</p>' if error else ""
    body = f"""<div class="card" style="max-width:460px;margin:48px auto">
<h1>Central Operacional Master</h1>
<p class="muted">Acesso web remoto — mesmo login do painel desktop.</p>
<form method="post" action="/login">
<label>E-mail administrativo</label><input name="email" type="email" required autocomplete="username"/>
<label>Senha</label><input name="password" type="password" required autocomplete="current-password"/>
{err}
<button type="submit">Entrar no sistema</button>
</form>
<p class="muted" style="margin-top:14px">Build {APP_BUILD} · {sistema_web_base()}</p>
</div>"""
    return _html_page(body, title="Login — Sistema Master")


def _dashboard_html(admin, stats=None):
    stats = stats or {}
    admin_name = admin.get("nome") or "Administrador"
    admin_email = admin.get("email") or ""
    tiles = [
        ("API Master", api_base_url(), "Gateway publico e integracoes"),
        ("Motor / Rede (QR)", engine_base(), "Reservas por rede e colaborador"),
        ("Portal Motorista", driver_portal_base(), "Painel do motorista parceiro"),
        ("Portal Empresa", company_portal_base(), "Login corporativo por empresa cliente"),
    ]
    tile_html = "".join(
        f'<div class="tile"><b>{title}</b><a href="{url}" target="_blank" rel="noopener">{url}</a><p class="muted">{hint}</p></div>'
        for title, url, hint in tiles
    )
    kpi = f"""
<div class="grid" style="margin-bottom:18px">
<div class="tile"><span class="muted">Empresas ativas</span><b style="font-size:1.4rem;color:#0f172a">{stats.get('companies_active', '—')}</b></div>
<div class="tile"><span class="muted">Motoristas</span><b style="font-size:1.4rem;color:#0f172a">{stats.get('drivers_homologated', '—')}</b></div>
<div class="tile"><span class="muted">Cidades cobertas</span><b style="font-size:1.4rem;color:#0f172a">{stats.get('cities_covered', '—')}</b></div>
<div class="tile"><span class="muted">Pontos operacionais</span><b style="font-size:1.4rem;color:#0f172a">{stats.get('operational_points_total', '—')}</b></div>
</div>"""
    body = f"""<div class="card">
<div class="top"><div><h1>Sistema Master Web</h1><p class="muted">{admin_name} · {admin_email}</p></div>
<form method="post" action="/logout"><button type="submit" style="background:#dc2626">Sair</button></form></div>
{kpi}
<h2 style="margin:0 0 8px;font-size:1.1rem">Portais da plataforma</h2>
<p class="muted">Use os links abaixo para acessar cada superficie web. O painel desktop completo (Tkinter) continua disponivel localmente com o mesmo login.</p>
<div class="grid">{tile_html}</div>
</div>"""
    return _html_page(body, title="Dashboard — Sistema Master")


def _load_stats(app):
    try:
        from .public_dtos import build_public_statistics_legacy

        return build_public_statistics_legacy(app)
    except Exception:
        return {}


def _build_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def _cookies(self):
            raw = self.headers.get("Cookie", "")
            cookies = {}
            for chunk in raw.split(";"):
                if "=" in chunk:
                    key, value = chunk.strip().split("=", 1)
                    cookies[key] = value
            return cookies

        def _redirect(self, location, *, token=None):
            self.send_response(302)
            self.send_header("Location", location)
            if token:
                self.send_header("Set-Cookie", f"sistema_token={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800")
            self.end_headers()

        def _html(self, code, content):
            body = content.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_form(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            return {k: v[0] if v else "" for k, v in parse_qs(raw).items()}

        def do_GET(self):
            path = urlparse(self.path).path
            token = self._cookies().get("sistema_token", "")
            admin = _get_session(token)
            if path in {"", "/"}:
                if admin:
                    return self._html(200, _dashboard_html(admin, _load_stats(app)))
                return self._html(200, _login_html())
            if path == "/dashboard" and admin:
                return self._html(200, _dashboard_html(admin, _load_stats(app)))
            if path == "/api/health":
                body = json.dumps({"ok": True, "service": "sistema_web", "build": APP_BUILD}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/login":
                form = self._read_form()
                admin, error = authenticate_admin(form.get("email"), form.get("password"))
                if not admin:
                    return self._html(401, _login_html(error or "Login invalido."))
                token = _new_session(admin)
                return self._redirect("/dashboard", token=token)
            if path == "/logout":
                token = self._cookies().get("sistema_token", "")
                _revoke_session(token)
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", "sistema_token=; Path=/; Max-Age=0")
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

    return Handler


def start_sistema_web_server(app):
    if getattr(app, "sistema_web_server", None):
        return sistema_web_base()
    handler = _build_handler(app)
    server = ThreadingHTTPServer((bind_host(), SISTEMA_WEB_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    app.sistema_web_server = server
    return sistema_web_base()
