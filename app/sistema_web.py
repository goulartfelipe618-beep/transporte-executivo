"""Painel web completo do Sistema Master — sistema.transporteexecutivo.com."""
from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .admin_auth import authenticate_admin
from .bind_host import bind_host
from .branding import brand_display_name
from .sistema_web_layout import panel_page
from .sistema_web_modules import normalize_module_key, render_module
from .cdn.urls import static_url
from .version import APP_BUILD

SISTEMA_WEB_PORT = 8772
_SESSIONS = {}
_LOGIN_CAPTCHAS = {}
_LOGIN_IMAGES_DIR = Path(__file__).resolve().parent / "master" / "static" / "master" / "images" / "login"
_CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def _new_captcha_code(length: int = 6) -> str:
    return "".join(secrets.choice(_CAPTCHA_ALPHABET) for _ in range(length))


def _issue_login_captcha():
    key = secrets.token_urlsafe(16)
    code = _new_captcha_code()
    _LOGIN_CAPTCHAS[key] = code
    return key, code


def _verify_login_captcha(key, value):
    expected = _LOGIN_CAPTCHAS.pop(str(key or "").strip(), "")
    provided = str(value or "").strip()
    if not expected or not provided:
        return False
    return secrets.compare_digest(str(expected), provided)


def _new_session(admin):
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = dict(admin or {})
    return token


def _get_session(token):
    return _SESSIONS.get(str(token or "").strip())


def _revoke_session(token):
    _SESSIONS.pop(str(token or "").strip(), None)


def _login_html(error="", *, email="", captcha_key="", captcha_code=""):
    err = (
        f'<div class="error-box">{error}</div>'
        if error
        else ""
    )
    email_value = email.replace('"', "&quot;")
    brand = brand_display_name()
    if not captcha_key or not captcha_code:
        captcha_key, captcha_code = _issue_login_captcha()
    key_value = captcha_key.replace('"', "&quot;")
    hero_bg = static_url("master/images/login/hero-bg.png")
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Login — {brand}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;font-family:Inter,Segoe UI,system-ui,sans-serif}}
.backdrop{{position:fixed;inset:0;background:url("{hero_bg}") center/cover no-repeat;transform:scale(1.02)}}
.overlay{{position:fixed;inset:0;background:linear-gradient(180deg,rgba(8,12,22,.35),rgba(8,12,22,.55))}}
.stage{{position:relative;z-index:2;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:32px 20px}}
.panel{{width:100%;max-width:420px;background:#fff;border-radius:14px;padding:36px 34px 28px;box-shadow:0 28px 80px rgba(0,0,0,.38)}}
.title{{margin:0 0 4px;text-align:center;font-size:1.75rem;font-weight:700;color:#374151}}
.brand{{margin:0 0 26px;text-align:center;font-size:.82rem;color:#6b7280}}
.field{{margin-bottom:18px}}label{{display:block;margin-bottom:7px;font-size:.88rem;font-weight:600;color:#374151}}
input{{width:100%;padding:12px 14px;border:1px solid #d1d5db;border-radius:8px;font-size:.95rem}}
input:focus{{outline:none;border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.15)}}
.captcha-row{{display:flex;gap:8px;margin-bottom:8px}}.captcha-code{{flex:1;padding:10px;border:1px dashed #d1d5db;border-radius:8px;background:#f9fafb;font-family:Consolas,monospace;font-size:1.05rem;font-weight:700;text-align:center}}
.forgot{{text-align:right;margin:-4px 0 20px}}.forgot a{{color:#2563eb;font-size:.84rem;text-decoration:underline}}
button[type=submit]{{display:block;width:100%;max-width:200px;margin:0 auto;padding:11px 20px;border:2px solid #2563eb;border-radius:8px;background:#fff;color:#2563eb;font-weight:700;text-transform:uppercase;cursor:pointer}}
button[type=submit]:hover{{background:#2563eb;color:#fff}}
.error-box{{margin:0 0 16px;padding:11px 14px;border-radius:8px;background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;font-size:.84rem}}
.note{{margin-top:22px;padding-top:18px;border-top:1px solid #f3f4f6;text-align:center;font-size:.76rem;color:#9ca3af}}
.foot{{margin:18px 0 0;text-align:center;color:rgba(255,255,255,.82);font-size:.74rem}}
</style></head><body>
<div class="backdrop"></div><div class="overlay"></div>
<main class="stage"><div class="panel">
<h1 class="title">Login</h1><p class="brand">{brand}</p>
{err}
<form method="post" action="/login">
<div class="field"><label>E-mail</label><input name="email" type="text" required autocomplete="username" placeholder="Digite seu e-mail" value="{email_value}"/></div>
<div class="field"><label>Senha</label><input name="password" type="password" required autocomplete="current-password" placeholder="Digite sua senha"/></div>
<div class="field"><label>Código de segurança</label><div class="captcha-row"><div class="captcha-code">{captcha_code}</div></div><input name="captcha" type="text" required autocomplete="off" placeholder="Digite o código acima"/></div>
<input type="hidden" name="captcha_key" value="{key_value}"/>
<div class="forgot"><a href="#">Esqueceu a senha?</a></div>
<button type="submit">Enviar</button>
</form>
<p class="note">Nunca compartilhe sua senha. Verifique o código antes de entrar.</p>
</div><p class="foot">© 2026 {brand}</p></main>
</body></html>"""


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

            if path == "/api/deploy-info":
                mode = "web"
                try:
                    stamp = Path("/app/.nexus_sistema_ui").read_text(encoding="utf-8").strip()
                except OSError:
                    stamp = "unknown"
                body = json.dumps(
                    {
                        "ok": True,
                        "service": "sistema_web",
                        "mode": mode,
                        "build": APP_BUILD,
                        "stamp": stamp,
                        "vnc_removed": True,
                        "login_url": "/",
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("X-Nexus-Deploy", f"web-{APP_BUILD}")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path == "/api/health":
                body = json.dumps({"ok": True, "service": "sistema_web", "build": APP_BUILD, "panel": True}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path in {"/vnc.html", "/vnc_lite.html", "/vnc_auto.html"}:
                return self._redirect("/")

            if path.startswith("/static/login/"):
                filename = Path(path).name
                image_path = _LOGIN_IMAGES_DIR / filename
                if image_path.is_file():
                    data = image_path.read_bytes()
                    content_type = "image/jpeg" if filename.lower().endswith(".jpg") else "application/octet-stream"
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return

            if path in {"/", "", "/login"}:
                if admin:
                    return self._redirect("/painel/abrangencia")
                body = _login_html().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("X-Nexus-Deploy", f"web-{APP_BUILD}")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

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
            if path in {"/", "", "/login"}:
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
                if not _verify_login_captcha(form.get("captcha_key"), form.get("captcha")):
                    return self._html(
                        401,
                        _login_html(
                            "Codigo de seguranca invalido.",
                            email=form.get("email", ""),
                        ),
                    )
                admin, error = authenticate_admin(form.get("email"), form.get("password"))
                if not admin:
                    return self._html(
                        401,
                        _login_html(
                            error or "E-mail ou senha invalidos.",
                            email=form.get("email", ""),
                        ),
                    )
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
