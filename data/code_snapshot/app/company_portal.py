"""Portal da Empresa — nivel 2 da plataforma, isolado por tenant."""
import base64
import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .catalog import published_items
from .company_model import (
    append_portal_activity,
    company_key,
    company_reservations,
    company_transport_requests,
    find_company,
    find_company_by_path,
    find_company_user,
)
from .portal_landing import company_portal_landing
from .company_portal_gateway import (
    gateway_airports,
    gateway_coverage,
    gateway_hotels,
    gateway_locations,
    gateway_vehicles,
)
from .company_portal_services import (
    dashboard_payload,
    delete_cost_center,
    delete_passenger,
    delete_user,
    export_excel_csv,
    export_pdf_html,
    finance_payload,
    history_payload,
    list_cost_centers,
    list_passengers,
    list_users,
    needs_approval,
    request_dto,
    save_cost_center,
    save_passenger,
    save_user,
)
from .company_portal_ui import render_company_portal_page
from .portal_auth import (
    USER_TYPE_COMPANY,
    company_can,
    company_permissions,
    create_session,
    get_valid_session,
    is_password_hash,
    log_portal_event,
    prepare_password_field,
    revoke_session,
    touch_session,
    verify_password,
)
from .pricing_engine import estimate_route, published_vehicle_catalog

COMPANY_PORTAL_PORT = 8766

_SESSION_KEYS = {"slug", "token", "format"}


def _payload_data(data):
    return {key: value for key, value in data.items() if key not in _SESSION_KEYS}


def company_portal_url(app):
    if getattr(app, "company_portal_server", None):
        return f"http://127.0.0.1:{COMPANY_PORTAL_PORT}"
    return start_company_portal_server(app)


def _resolve_cost_center_fields(company, centro_custo_id):
    centro = None
    for item in company.get("centros_custo") or []:
        if str(item.get("id")) == str(centro_custo_id):
            centro = item
            break
    if not centro:
        return "", ""
    return centro.get("id", ""), centro.get("nome", "")


def _create_transport_request(app, company, payload, user):
    if not hasattr(app, "transport_requests"):
        app.transport_requests = []
    request_id = f"treq-{len(app.transport_requests) + 1:06d}"
    cc_id, cc_name = _resolve_cost_center_fields(company, payload.get("centro_custo_id", ""))
    require_approval = needs_approval(user)
    status = "Aguardando aprovacao" if require_approval else "Recebida"
    record = {
        "id": request_id,
        "company_id": company.get("id"),
        "company_nome": company.get("razao_social") or company.get("nome_fantasia", ""),
        "origem": payload.get("origem", ""),
        "destino": payload.get("destino", ""),
        "data": payload.get("data", ""),
        "hora": payload.get("hora", ""),
        "passageiros": payload.get("passageiros", "1"),
        "categoria": payload.get("categoria", ""),
        "centro_custo_id": cc_id,
        "centro_custo_nome": cc_name,
        "nome": user.get("nome", ""),
        "telefone": user.get("telefone", ""),
        "email": user.get("email", ""),
        "origem_fonte": "Portal Empresa",
        "status": status,
        "approval_status": status,
        "observacoes": f'Solicitacao via portal por {user.get("email", "")}',
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    app.transport_requests.insert(0, record)
    reservation = None
    if not require_approval:
        reservation = _create_company_reservation(app, company, record)
    append_portal_activity(
        company,
        "Solicitacao criada",
        f'{record.get("id", "")} — {status}',
        user_id=user.get("id", ""),
        referencia_id=record.get("id", ""),
    )
    log_portal_event(
        app,
        "portal.company.request_created",
        f"Solicitacao {record.get('id', '')} via portal",
        user_type=USER_TYPE_COMPANY,
        user_id=user.get("id", ""),
        referencia_id=record.get("id", ""),
        payload={"company_id": company.get("id", ""), "approval_required": require_approval},
    )
    if hasattr(app, "save_state"):
        app.save_state()
    record["approval_required"] = require_approval
    record["reservation_numero"] = reservation.get("numero") if reservation else ""
    return record


def _create_company_reservation(app, company, request):
    numbers = []
    for item in getattr(app, "reservations", []):
        try:
            numbers.append(int(str(item.get("numero", "")).replace("#", "")))
        except ValueError:
            pass
    numero = f"#{max(numbers, default=1000) + 1}"
    company_name = company.get("razao_social") or company.get("nome_fantasia") or company.get("nome", "")
    reservation = {
        "numero": numero,
        "cliente": company_name,
        "company_id": company.get("id"),
        "contato": request.get("nome", ""),
        "email": request.get("email", ""),
        "tipo": "Transfer",
        "trajeto": f'{request.get("origem", "")} -> {request.get("destino", "")}',
        "data": f'{request.get("data", "")} {request.get("hora", "")}'.strip(),
        "motorista": "",
        "driver_id": "",
        "valor": "",
        "status": "Pendente",
        "origem_fonte": "Portal Empresa",
        "transport_request_id": request.get("id"),
        "centro_custo_id": request.get("centro_custo_id", ""),
        "centro_custo_nome": request.get("centro_custo_nome", ""),
        "observacoes": f'Categoria: {request.get("categoria", "")} | Passageiros: {request.get("passageiros", "")}',
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    app.reservations.insert(0, reservation)
    return reservation


def _approve_transport_request(app, company, request_id, user):
    request = next((r for r in company_transport_requests(app, company) if str(r.get("id")) == str(request_id)), None)
    if not request:
        raise ValueError("solicitacao_nao_encontrada")
    if str(request.get("approval_status", request.get("status", ""))).lower() not in {"aguardando aprovacao", "recebida", "em analise"}:
        raise ValueError("solicitacao_nao_pendente")
    request["status"] = "Aprovada"
    request["approval_status"] = "Aprovada"
    request["aprovado_por"] = user.get("id", "")
    request["aprovado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    reservation = _create_company_reservation(app, company, request)
    append_portal_activity(company, "Solicitacao aprovada", request_id, user_id=user.get("id", ""), referencia_id=request_id)
    log_portal_event(
        app,
        "portal.company.request_approved",
        f"Solicitacao {request_id} aprovada",
        user_type=USER_TYPE_COMPANY,
        user_id=user.get("id", ""),
        referencia_id=request_id,
    )
    if hasattr(app, "save_state"):
        app.save_state()
    return {"request": request_dto(request), "reservation_numero": reservation.get("numero")}


def _reject_transport_request(app, company, request_id, user, motivo=""):
    request = next((r for r in company_transport_requests(app, company) if str(r.get("id")) == str(request_id)), None)
    if not request:
        raise ValueError("solicitacao_nao_encontrada")
    request["status"] = "Rejeitada"
    request["approval_status"] = "Rejeitada"
    request["rejeitado_por"] = user.get("id", "")
    request["motivo_rejeicao"] = str(motivo or "")
    request["atualizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    append_portal_activity(company, "Solicitacao rejeitada", request_id, user_id=user.get("id", ""), referencia_id=request_id)
    log_portal_event(
        app,
        "portal.company.request_rejected",
        f"Solicitacao {request_id} rejeitada",
        user_type=USER_TYPE_COMPANY,
        user_id=user.get("id", ""),
        referencia_id=request_id,
    )
    if hasattr(app, "save_state"):
        app.save_state()
    return request_dto(request)


def _pending_approvals(app, company):
    items = []
    for request in company_transport_requests(app, company):
        status = str(request.get("approval_status", request.get("status", ""))).lower()
        if status in {"aguardando aprovacao", "recebida", "em analise"}:
            items.append(request_dto(request))
    return items


def _build_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
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

        def _session(self, data):
            session = get_valid_session(app, data.get("token", ""))
            if not session or session.get("user_type") != USER_TYPE_COMPANY:
                return None, None, None
            touch_session(app, session.get("session_id"))
            company = find_company(app, session.get("slug"))
            if not company or not company.get("portal_ativo", True):
                return None, None, None
            user = next((u for u in company.get("usuarios") or [] if u.get("id") == session.get("user_id")), None)
            if not user or user.get("status") != "Ativo":
                return None, None, None
            return company, user, session

        def _require_permission(self, user, action):
            return company_can(user.get("perfil"), action)

        def _serve_portal(self, company):
            if not company:
                self.send_response(404)
                self.end_headers()
                return
            slug = company_key(company)
            name = company.get("razao_social") or company.get("nome_fantasia") or "Empresa"
            body = render_company_portal_page(slug, name).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path in {"", "/"}:
                body = company_portal_landing().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path.startswith("/empresa/"):
                slug = unquote(path.split("/empresa/", 1)[1]).strip("/").split("/")[0]
                return self._serve_portal(find_company(app, slug))
            clean = unquote(path).strip("/")
            parts = [part for part in clean.split("/") if part]
            if len(parts) == 2 and parts[0].lower().startswith("emp-"):
                return self._serve_portal(find_company_by_path(app, parts[0], parts[1]))
            self._json(404, {"error": "not_found"})

        def do_HEAD(self):
            path = urlparse(self.path).path
            if path in {"", "/"}:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                return
            if path.startswith("/empresa/"):
                slug = unquote(path.split("/empresa/", 1)[1]).strip("/").split("/")[0]
                self.send_response(200 if find_company(app, slug) else 404)
                self.end_headers()
                return
            clean = unquote(path).strip("/")
            parts = [part for part in clean.split("/") if part]
            if len(parts) == 2 and parts[0].lower().startswith("emp-"):
                company = find_company_by_path(app, parts[0], parts[1])
                self.send_response(200 if company else 404)
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            data = self._read_json()
            path = urlparse(self.path).path
            slug = data.get("slug", "")

            if path == "/api/company/login":
                company = find_company(app, slug)
                if not company or not company.get("portal_ativo", True):
                    return self._json(404, {"ok": False, "error": "Portal indisponivel"})
                user = find_company_user(company, data.get("email", ""))
                if not user or user.get("status") != "Ativo":
                    return self._json(401, {"ok": False, "error": "Credenciais invalidas"})
                password = str(data.get("password", ""))
                if not verify_password(password, user.get("senha", "")):
                    return self._json(401, {"ok": False, "error": "Credenciais invalidas"})
                if not is_password_hash(user.get("senha", "")):
                    user["senha"] = prepare_password_field(password)
                session_id, session = create_session(
                    app,
                    USER_TYPE_COMPANY,
                    user.get("id"),
                    tenant_id=company.get("id", ""),
                    slug=company_key(company),
                    perfil=user.get("perfil", ""),
                )
                perms = company_permissions(user.get("perfil"))
                log_portal_event(
                    app,
                    "portal.company.login",
                    f"Login {user.get('email', '')} ({company.get('id', '')})",
                    user_type=USER_TYPE_COMPANY,
                    user_id=user.get("id", ""),
                    referencia_id=company.get("id", ""),
                )
                if hasattr(app, "save_state"):
                    app.save_state()
                return self._json(
                    200,
                    {
                        "ok": True,
                        "token": session_id,
                        "expires_at": session.get("expires_at"),
                        "permissions": perms,
                        "user": {"nome": user.get("nome"), "perfil": user.get("perfil"), "id": user.get("id")},
                    },
                )

            if path == "/api/company/logout":
                token = data.get("token", "")
                session = get_valid_session(app, token)
                if session:
                    revoke_session(app, token)
                    log_portal_event(
                        app,
                        "portal.company.logout",
                        f"Logout usuario {session.get('user_id', '')}",
                        user_type=USER_TYPE_COMPANY,
                        user_id=session.get("user_id", ""),
                    )
                    if hasattr(app, "save_state"):
                        app.save_state()
                return self._json(200, {"ok": True})

            company, user, _session = self._session(data)
            if not company:
                return self._json(401, {"ok": False, "error": "Sessao invalida"})

            perms = company_permissions(user.get("perfil"))

            def ok(**payload):
                payload.setdefault("permissions", perms)
                payload["ok"] = True
                payload["user"] = {"nome": user.get("nome"), "perfil": user.get("perfil"), "id": user.get("id")}
                return self._json(200, payload)

            if path == "/api/company/dashboard":
                if not self._require_permission(user, "dashboard"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(**dashboard_payload(app, company))

            if path == "/api/company/history":
                if not self._require_permission(user, "history"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(**history_payload(app, company, **_payload_data(data)))

            if path == "/api/company/users/list":
                if not self._require_permission(user, "users"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(items=list_users(company))

            if path == "/api/company/users/save":
                if not self._require_permission(user, "users"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                try:
                    item = save_user(company, data, actor=user)
                    if data.get("senha"):
                        for row in company.get("usuarios") or []:
                            if row.get("id") == item.get("id"):
                                row["senha"] = prepare_password_field(data.get("senha"))
                    if hasattr(app, "save_state"):
                        app.save_state()
                    return ok(item=item)
                except ValueError as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})

            if path == "/api/company/users/delete":
                if not self._require_permission(user, "users"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                try:
                    delete_user(company, data.get("user_id"), actor=user)
                    if hasattr(app, "save_state"):
                        app.save_state()
                    return ok()
                except ValueError as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})

            if path in {"/api/company/cost-centers/list", "/api/company/cost-centers"}:
                if not self._require_permission(user, "cost_centers"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(items=list_cost_centers(company))

            if path == "/api/company/cost-centers/save":
                if not self._require_permission(user, "cost_centers"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                try:
                    item = save_cost_center(company, data, actor=user)
                    if hasattr(app, "save_state"):
                        app.save_state()
                    return ok(item=item)
                except ValueError as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})

            if path == "/api/company/cost-centers/delete":
                if not self._require_permission(user, "cost_centers"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                delete_cost_center(company, data.get("centro_id"), actor=user)
                if hasattr(app, "save_state"):
                    app.save_state()
                return ok()

            if path == "/api/company/passengers/list":
                if not self._require_permission(user, "passengers"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(items=list_passengers(company))

            if path == "/api/company/passengers/save":
                if not self._require_permission(user, "passengers"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                try:
                    item = save_passenger(company, data, actor=user)
                    if hasattr(app, "save_state"):
                        app.save_state()
                    return ok(item=item)
                except ValueError as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})

            if path == "/api/company/passengers/delete":
                if not self._require_permission(user, "passengers"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                delete_passenger(company, data.get("passenger_id"), actor=user)
                if hasattr(app, "save_state"):
                    app.save_state()
                return ok()

            if path == "/api/company/finance":
                if not self._require_permission(user, "finance"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(**finance_payload(app, company, **_payload_data(data)))

            if path == "/api/company/export":
                if not self._require_permission(user, "export"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                fmt = str(data.get("format", "excel")).lower()
                if fmt == "pdf":
                    html = export_pdf_html(app, company, **_payload_data(data))
                    return ok(content=html, mime="text/html", filename="relatorio-financeiro.html")
                csv_data = export_excel_csv(app, company, **_payload_data(data))
                encoded = base64.b64encode(csv_data.encode("utf-8-sig")).decode("ascii")
                return ok(content=encoded, mime="text/csv", filename="relatorio-financeiro.csv")

            if path == "/api/company/approvals/list":
                if not self._require_permission(user, "approve"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(items=_pending_approvals(app, company))

            if path == "/api/company/approve":
                if not self._require_permission(user, "approve"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                try:
                    result = _approve_transport_request(app, company, data.get("request_id"), user)
                    return ok(**result)
                except ValueError as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})

            if path == "/api/company/reject":
                if not self._require_permission(user, "approve"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                try:
                    item = _reject_transport_request(app, company, data.get("request_id"), user, data.get("motivo", ""))
                    return ok(item=item)
                except ValueError as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})

            if path == "/api/company/gateway/locations":
                if not self._require_permission(user, "locations"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                payload, source = gateway_locations(app, type_filter=data.get("type", ""), state=data.get("state", ""), city=data.get("city", ""))
                return ok(items=payload.get("items", []), total=payload.get("total", 0), source=source)

            if path == "/api/company/gateway/coverage":
                if not self._require_permission(user, "coverage"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                payload, source = gateway_coverage(app)
                payload["source"] = source
                return ok(**payload)

            if path == "/api/company/gateway/airports":
                if not self._require_permission(user, "airports"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                payload, source = gateway_airports(app)
                return ok(items=payload.get("items", []), total=payload.get("total", 0), source=source)

            if path == "/api/company/gateway/hotels":
                if not self._require_permission(user, "hotels"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                payload, source = gateway_hotels(app)
                return ok(items=payload.get("items", []), total=payload.get("total", 0), source=source)

            if path == "/api/company/gateway/vehicles":
                if not self._require_permission(user, "vehicles"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                payload, source = gateway_vehicles(app)
                return ok(items=payload.get("items", []), total=payload.get("total", 0), source=source)

            if path == "/api/company/vehicles":
                if not self._require_permission(user, "vehicles"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(items=published_vehicle_catalog(app))

            if path == "/api/company/hotels":
                if not self._require_permission(user, "hotels"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(items=published_items(getattr(app, "hotels", [])))

            if path == "/api/company/airports":
                if not self._require_permission(user, "airports"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                return ok(items=published_items(getattr(app, "airports", [])))

            if path == "/api/company/quote":
                if not self._require_permission(user, "calculator"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                quote = estimate_route(app, data.get("origem", ""), data.get("destino", ""), data.get("categoria", ""), km=data.get("km") or 0)
                if not quote.get("options"):
                    return self._json(200, {"ok": False, "error": "Sem parametros operacionais"})
                return ok(quote=quote)

            if path == "/api/company/request":
                if not self._require_permission(user, "request"):
                    return self._json(403, {"ok": False, "error": "sem_permissao"})
                if not data.get("origem") or not data.get("destino"):
                    return self._json(400, {"ok": False, "error": "Origem e destino sao obrigatorios"})
                record = _create_transport_request(app, company, data, user)
                return ok(
                    id=record.get("id"),
                    approval_required=record.get("approval_required", False),
                    reservation_numero=record.get("reservation_numero", ""),
                )

            return self._json(404, {"ok": False, "error": "not_found"})

    return Handler


def start_company_portal_server(app):
    from .bind_host import bind_host, service_url

    if getattr(app, "company_portal_server", None):
        return service_url(COMPANY_PORTAL_PORT)
    server = ThreadingHTTPServer((bind_host(), COMPANY_PORTAL_PORT), _build_handler(app))
    app.company_portal_server = server
    threading.Thread(target=server.serve_forever, daemon=True, name="company-portal").start()
    return service_url(COMPANY_PORTAL_PORT)
