"""Painel web completo do Sistema Master — sistema.transporteexecutivo.com."""
from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .admin_auth import authenticate_admin
from .bind_host import bind_host
from .sistema_web_layout import panel_page
from .sistema_web_modules import normalize_module_key, render_module
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


def _login_html(error=""):
    err = f'<p class="error">{error}</p>' if error else ""
    body = f"""<div class="card" style="max-width:460px;margin:48px auto;background:#fff;border-radius:16px;padding:24px">
<h1>Central Operacional Master</h1>
<p class="muted">Painel web completo — mesmo login do desktop.</p>
<form method="post" action="/login">
<label>E-mail administrativo</label><input name="email" type="email" required autocomplete="username"/>
<label>Senha</label><input name="password" type="password" required autocomplete="current-password"/>
{err}
<button type="submit">Entrar no sistema</button>
</form>
<p class="muted" style="margin-top:14px">Build {APP_BUILD}</p>
</div>"""
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Login — Sistema Master</title>
<style>
body{{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:linear-gradient(160deg,#0f172a,#1e293b);min-height:100vh}}
.muted{{color:#64748b;font-size:.9rem}}label{{display:block;font-weight:600;margin:12px 0 6px}}
input{{width:100%;padding:11px;border:1px solid #e2e8f0;border-radius:10px;box-sizing:border-box}}
button{{margin-top:16px;padding:11px 16px;border:0;border-radius:10px;background:#2563eb;color:#fff;font-weight:600;cursor:pointer;width:100%}}
.error{{color:#dc2626;font-size:.85rem;margin-top:10px}}
</style></head><body>{body}</body></html>"""


def _render_panel(app, admin, module_key):
    content = render_module(app, module_key)
    return panel_page(admin, module_key, content)


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

        def _require_admin(self):
            token = self._cookies().get("sistema_token", "")
            admin = _get_session(token)
            if not admin:
                self._redirect("/")
                return None
            return admin

        def do_GET(self):
            path = urlparse(self.path).path.rstrip("/") or "/"
            token = self._cookies().get("sistema_token", "")
            admin = _get_session(token)

            if path == "/api/health":
                body = json.dumps({"ok": True, "service": "sistema_web", "build": APP_BUILD, "panel": True}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path in {"/", ""}:
                if admin:
                    return self._redirect("/painel/abrangencia")
                return self._html(200, _login_html())

            if path == "/dashboard":
                if admin:
                    return self._redirect("/painel/abrangencia")
                return self._redirect("/")

            if path.startswith("/painel"):
                admin = self._require_admin()
                if not admin:
                    return
                slug = path[len("/painel/"):].strip("/") if path != "/painel" else ""
                module_key = normalize_module_key(slug)
                if slug and module_key is None:
                    return self._html(404, panel_page(admin, "ABRANGENCIA", '<div class="empty">Modulo nao encontrado.</div>'))
                return self._html(200, _render_panel(app, admin, module_key or "ABRANGENCIA"))

            self.send_response(404)
            self.end_headers()

        def do_HEAD(self):
            path = urlparse(self.path).path.rstrip("/") or "/"
            if path in {"/", ""}:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if path == "/api/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                return
            if path.startswith("/painel"):
                self.send_response(200 if _get_session(self._cookies().get("sistema_token", "")) else 302)
                self.end_headers()
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
                return self._redirect("/painel/abrangencia", token=token)
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
        from .portal_urls import sistema_web_base

        return sistema_web_base()
    handler = _build_handler(app)
    server = ThreadingHTTPServer((bind_host(), SISTEMA_WEB_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    app.sistema_web_server = server
    from .portal_urls import sistema_web_base

    return sistema_web_base()
