import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .portal_landing import driver_portal_landing
from .portal_auth import (
    USER_TYPE_DRIVER,
    activation_token_valid,
    create_session,
    driver_has_password,
    driver_reservations_for,
    find_driver_by_id,
    get_valid_session,
    log_portal_event,
    reservation_belongs_to_driver,
    revoke_session,
    set_driver_password,
    touch_session,
    verify_driver_password,
)

PORTAL_PORT = 8765


def driver_key(driver):
    raw = driver.get("cpf") or driver.get("nome") or "motorista"
    return "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")


def _find_driver(app, slug):
    return next((d for d in getattr(app, "drivers", []) if driver_key(d) == slug), None)


def update_reservation_status(app, numero, status, driver):
    for item in getattr(app, "reservations", []):
        if str(item.get("numero")) != str(numero):
            continue
        if not reservation_belongs_to_driver(item, driver):
            return False
        item["status"] = status
        log_portal_event(
            app,
            "portal.driver.reservation_status",
            f"Reserva {numero} -> {status}",
            user_type=USER_TYPE_DRIVER,
            user_id=driver.get("id", ""),
            referencia_id=str(numero),
            payload={"status": status},
        )
        if hasattr(app, "save_state"):
            app.save_state()
        return True
    return False


def _resolve_driver_session(app, data):
    session = get_valid_session(app, data.get("token", ""))
    if not session or session.get("user_type") != USER_TYPE_DRIVER:
        return None, None
    driver = find_driver_by_id(app, session.get("user_id"))
    if not driver:
        return None, None
    touch_session(app, session.get("session_id"))
    return session, driver


def _build_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_a):
            return

        def _json(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw or b"{}")

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path in {"", "/"}:
                body = driver_portal_landing().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path.startswith("/driver/"):
                slug = unquote(path.split("/driver/", 1)[1]).strip("/").split("?")[0]
                driver = _find_driver(app, slug)
                if not driver:
                    self.send_response(404)
                    self.end_headers()
                    return
                query = parse_qs(parsed.query)
                activation_hint = ""
                if query.get("activation"):
                    activation_hint = "<p>Use o token de ativacao fornecido pelo administrador para definir sua senha via POST /api/driver/set-password.</p>"
                elif not driver_has_password(driver):
                    activation_hint = "<p>Portal ainda nao ativado. Solicite o token de ativacao ao administrador.</p>"
                html = (
                    f"<html><body><h1>Portal {driver.get('nome', '')}</h1>"
                    f"<p>Motorista ID: {driver.get('id', '')}</p>"
                    f"{activation_hint}"
                    f"<p>Endpoints: login, set-password (com token), reservations, status, logout.</p></body></html>"
                )
                self.send_response(200)
                self.end_headers()
                self.wfile.write(html.encode())
                return
            self._json(404, {"error": "not_found"})

        def do_HEAD(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path in {"", "/"}:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if path.startswith("/driver/"):
                slug = unquote(path.split("/driver/", 1)[1]).strip("/").split("?")[0]
                self.send_response(200 if _find_driver(app, slug) else 404)
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            data = self._read_json()
            path = urlparse(self.path).path
            slug = str(data.get("slug", "")).strip()

            if path == "/api/driver/set-password":
                driver = _find_driver(app, slug)
                if not driver:
                    return self._json(404, {"ok": False, "error": "motorista_nao_encontrado"})
                if driver_has_password(driver):
                    return self._json(403, {"ok": False, "error": "senha_ja_definida_solicite_admin"})
                if not activation_token_valid(driver, data.get("activation_token", "")):
                    return self._json(403, {"ok": False, "error": "token_ativacao_invalido"})
                password = str(data.get("password", "")).strip()
                if len(password) < 6:
                    return self._json(400, {"ok": False, "error": "senha_muito_curta"})
                set_driver_password(driver, password)
                log_portal_event(
                    app,
                    "portal.driver.password_set",
                    f"Senha definida para {driver.get('id', '')}",
                    user_type=USER_TYPE_DRIVER,
                    user_id=driver.get("id", ""),
                )
                if hasattr(app, "save_state"):
                    app.save_state()
                return self._json(200, {"ok": True})

            if path == "/api/driver/login":
                driver = _find_driver(app, slug)
                if not driver or not driver_has_password(driver):
                    return self._json(401, {"ok": False, "error": "credenciais_invalidas"})
                if not verify_driver_password(driver, data.get("password", "")):
                    return self._json(401, {"ok": False, "error": "credenciais_invalidas"})
                session_id, session = create_session(app, USER_TYPE_DRIVER, driver.get("id"), slug=slug)
                log_portal_event(
                    app,
                    "portal.driver.login",
                    f"Login motorista {driver.get('id', '')}",
                    user_type=USER_TYPE_DRIVER,
                    user_id=driver.get("id", ""),
                )
                if hasattr(app, "save_state"):
                    app.save_state()
                return self._json(
                    200,
                    {
                        "ok": True,
                        "token": session_id,
                        "expires_at": session.get("expires_at"),
                        "driver_id": driver.get("id"),
                    },
                )

            if path == "/api/driver/logout":
                token = data.get("token", "")
                session = get_valid_session(app, token)
                if session:
                    revoke_session(app, token)
                    log_portal_event(
                        app,
                        "portal.driver.logout",
                        f"Logout motorista {session.get('user_id', '')}",
                        user_type=USER_TYPE_DRIVER,
                        user_id=session.get("user_id", ""),
                    )
                    if hasattr(app, "save_state"):
                        app.save_state()
                return self._json(200, {"ok": True})

            session, driver = _resolve_driver_session(app, data)
            if not driver:
                return self._json(401, {"ok": False, "error": "sessao_invalida"})

            if path == "/api/driver/reservations":
                items = [
                    {
                        "numero": r.get("numero"),
                        "cliente": r.get("cliente"),
                        "data": r.get("data"),
                        "trajeto": r.get("trajeto"),
                        "status": r.get("status"),
                        "driver_id": r.get("driver_id"),
                    }
                    for r in driver_reservations_for(app, driver)
                ]
                return self._json(200, {"ok": True, "items": items})

            if path == "/api/driver/status":
                ok = update_reservation_status(app, data.get("numero"), data.get("status"), driver)
                return self._json(200 if ok else 403, {"ok": ok, "error": None if ok else "reserva_nao_permitida"})

            return self._json(404, {"error": "not_found"})

    return Handler


def start_driver_portal_server(app):
    from .bind_host import service_url, bind_host

    if getattr(app, "driver_portal_server", None):
        return service_url(PORTAL_PORT)
    server = ThreadingHTTPServer((bind_host(), PORTAL_PORT), _build_handler(app))
    app.driver_portal_server = server
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return service_url(PORTAL_PORT)
