import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .driver_portal_dtos import STATUS_ACTIONS, dashboard_dto, driver_finance_dto, profile_dto, reservation_dto
from .driver_portal_notifications import notifications_dto, sync_reservation_notifications
from .driver_portal_ui import render_driver_portal_page
from .portal_landing import driver_portal_landing
from .driver_portal_access import (
    activation_consumed_pending_password,
    activation_token_pending,
    driver_cpf_matches,
    try_consume_activation_token,
)
from .driver_portal_panel import (
    begin_totp_setup,
    cancel_driver_reservation,
    create_driver_client,
    create_driver_reservation,
    disable_driver_totp,
    enable_driver_totp,
    list_driver_clients,
    pdf_payload,
    public_panel_config,
    save_panel_config,
    update_driver_reservation,
    verify_driver_totp,
)
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


def _find_driver_reservation(app, driver, numero):
    target = str(numero or "").strip()
    if not target:
        return None
    for reservation in driver_reservations_for(app, driver):
        if str(reservation.get("numero", "")) == target:
            return reservation
    return None


def _reservation_actions(_reservation):
    return [{"key": a["key"], "label": a["label"], "status": a["status"]} for a in STATUS_ACTIONS]


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
                html = render_driver_portal_page(app, driver, slug)
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
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
                password = str(data.get("password", "")).strip()
                confirm = str(data.get("password_confirm", data.get("confirm_password", ""))).strip()
                if len(password) < 6:
                    return self._json(400, {"ok": False, "error": "senha_muito_curta"})
                if password != confirm:
                    return self._json(400, {"ok": False, "error": "senhas_nao_conferem"})

                session = get_valid_session(app, data.get("token", ""))
                if session and session.get("must_set_password"):
                    driver = find_driver_by_id(app, session.get("user_id"))
                    if not driver:
                        return self._json(404, {"ok": False, "error": "motorista_nao_encontrado"})
                    if driver_has_password(driver):
                        session.pop("must_set_password", None)
                        return self._json(403, {"ok": False, "error": "senha_ja_definida"})
                    set_driver_password(driver, password)
                    session.pop("must_set_password", None)
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

                driver = _find_driver(app, slug)
                if not driver:
                    return self._json(404, {"ok": False, "error": "motorista_nao_encontrado"})
                if driver_has_password(driver):
                    return self._json(403, {"ok": False, "error": "senha_ja_definida_solicite_admin"})
                if not activation_token_valid(driver, data.get("activation_token", "")):
                    return self._json(403, {"ok": False, "error": "token_ativacao_invalido"})
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
                if not driver:
                    return self._json(401, {"ok": False, "error": "credenciais_invalidas"})
                cpf_input = data.get("cpf") or data.get("identificacao") or slug
                if not driver_cpf_matches(driver, cpf_input):
                    return self._json(401, {"ok": False, "error": "credenciais_invalidas"})
                password = str(data.get("password", "")).strip()
                if not password:
                    return self._json(401, {"ok": False, "error": "credenciais_invalidas"})

                if driver_has_password(driver):
                    if not verify_driver_password(driver, password):
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
                            "requires_password_setup": False,
                        },
                    )

                if activation_consumed_pending_password(driver):
                    session = get_valid_session(app, data.get("token", ""))
                    if session and session.get("must_set_password"):
                        return self._json(
                            403,
                            {
                                "ok": False,
                                "error": "defina_sua_senha",
                                "requires_password_setup": True,
                                "token": session.get("session_id"),
                            },
                        )
                    return self._json(
                        403,
                        {
                            "ok": False,
                            "error": "token_ja_consumido",
                            "requires_password_setup": True,
                        },
                    )

                if not activation_token_pending(driver):
                    return self._json(401, {"ok": False, "error": "credenciais_invalidas"})

                if not try_consume_activation_token(driver, password):
                    return self._json(401, {"ok": False, "error": "credenciais_invalidas"})

                session_id, session = create_session(app, USER_TYPE_DRIVER, driver.get("id"), slug=slug)
                session["must_set_password"] = True
                log_portal_event(
                    app,
                    "portal.driver.activation_consumed",
                    f"Token consumido por {driver.get('id', '')}",
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
                        "requires_password_setup": True,
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
            if session.get("must_set_password") and path not in {"/api/driver/set-password", "/api/driver/logout"}:
                return self._json(
                    403,
                    {"ok": False, "error": "defina_sua_senha", "requires_password_setup": True},
                )

            if path == "/api/driver/dashboard":
                payload = dashboard_dto(app, driver, session)
                return self._json(200, {"ok": True, **payload})

            if path == "/api/driver/profile":
                return self._json(200, {"ok": True, "profile": profile_dto(driver)})

            if path == "/api/driver/reservations":
                items = [reservation_dto(app, r, driver) for r in driver_reservations_for(app, driver)]
                return self._json(200, {"ok": True, "items": items})

            if path == "/api/driver/finance":
                return self._json(200, {"ok": True, **driver_finance_dto(app, driver)})

            if path == "/api/driver/reservation":
                reservation = _find_driver_reservation(app, driver, data.get("numero"))
                if not reservation:
                    return self._json(403, {"ok": False, "error": "reserva_nao_permitida"})
                return self._json(
                    200,
                    {
                        "ok": True,
                        "item": reservation_dto(app, reservation, driver),
                        "actions": _reservation_actions(reservation),
                    },
                )

            if path == "/api/driver/clients":
                return self._json(200, {"ok": True, "items": list_driver_clients(app, driver)})

            if path == "/api/driver/client-create":
                try:
                    client = create_driver_client(app, driver, data)
                except Exception as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})
                return self._json(200, {"ok": True, "item": client})

            if path == "/api/driver/reservation-create":
                try:
                    reservation = create_driver_reservation(app, driver, data)
                except ValueError as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})
                return self._json(200, {"ok": True, "item": reservation_dto(app, reservation, driver)})

            if path == "/api/driver/reservation-update":
                ok, message = verify_driver_totp(driver, data.get("totp_code", ""))
                if not ok:
                    return self._json(403, {"ok": False, "error": message})
                ok, message = update_driver_reservation(app, driver, data.get("numero"), data)
                return self._json(200 if ok else 403, {"ok": ok, "error": message})

            if path == "/api/driver/reservation-cancel":
                ok, message = verify_driver_totp(driver, data.get("totp_code", ""))
                if not ok:
                    return self._json(403, {"ok": False, "error": message})
                ok, message = cancel_driver_reservation(app, driver, data.get("numero"))
                return self._json(200 if ok else 403, {"ok": ok, "error": message})

            if path == "/api/driver/reservation-pdf":
                try:
                    payload = pdf_payload(app, driver, data.get("numero"), data.get("via", "cliente"))
                except Exception as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})
                return self._json(200, {"ok": True, **payload})

            if path == "/api/driver/settings":
                return self._json(200, {"ok": True, "settings": public_panel_config(driver)})

            if path == "/api/driver/settings-save":
                ok, message = verify_driver_totp(driver, data.get("totp_code", ""))
                if not ok:
                    return self._json(403, {"ok": False, "error": message})
                settings = save_panel_config(driver, data)
                if hasattr(app, "save_state"):
                    app.save_state()
                return self._json(200, {"ok": True, "settings": settings})

            if path == "/api/driver/totp-setup":
                payload = begin_totp_setup(driver)
                if hasattr(app, "save_state"):
                    app.save_state()
                return self._json(200, {"ok": True, **payload})

            if path == "/api/driver/totp-enable":
                ok, message = enable_driver_totp(driver, data.get("totp_code", ""))
                if hasattr(app, "save_state"):
                    app.save_state()
                return self._json(200 if ok else 400, {"ok": ok, "error": message})

            if path == "/api/driver/totp-disable":
                ok, message = disable_driver_totp(driver, data.get("totp_code", ""))
                if hasattr(app, "save_state"):
                    app.save_state()
                return self._json(200 if ok else 403, {"ok": ok, "error": message})

            if path == "/api/driver/notifications":
                changed = sync_reservation_notifications(app, driver)
                if changed and hasattr(app, "save_state"):
                    app.save_state()
                return self._json(200, {"ok": True, "items": notifications_dto(driver)})

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
