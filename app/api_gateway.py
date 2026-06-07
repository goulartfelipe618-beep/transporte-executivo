"""Gateway HTTP v1 — fonte oficial de dados publicos para o Website (porta 8770)."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .operational_network import ensure_operational_network
from .partner_network_gateway import handle_network_get, handle_network_post
from .platform import (
    INBOUND_COLLECTIONS,
    INBOUND_NORMALIZERS,
    INBOUND_RECEIVED_EVENTS,
    ORIGIN_SITE,
    ensure_platform_collections,
    log_event,
    next_record_id,
)
from .platform_contract import (
    API_INBOUND_COMPANY_LEAD,
    API_INBOUND_DRIVER_APPLICATION,
    API_INBOUND_RESERVATION_REQUEST,
    API_PUBLIC_COVERAGE,
    API_PUBLIC_EVENTS,
    API_PUBLIC_LOCATIONS_AGGREGATE,
    API_PUBLIC_LOCATIONS_BASE,
    API_PUBLIC_LOCATION_DETAIL_BASE,
    API_PUBLIC_AIRPORTS,
    API_PUBLIC_HOTELS,
    API_PUBLIC_STATISTICS,
    API_PUBLIC_STATS,
    API_PUBLIC_SYNC_LOCATIONS,
    API_PUBLIC_SYNC_STATISTICS,
    API_PUBLIC_VEHICLES,
    CONTRACT_VERSION,
    ENTITY_CITY,
    ENTITY_STATE,
    ENV_GATEWAY_HOST,
    ENV_GATEWAY_WEBHOOK_SECRET,
    ENV_WEBHOOK_OUTBOUND_URL,
    EVENT_LEAD_CREATED,
    GATEWAY_PORT,
    INBOUND_EVENT_COMPANY_LEAD,
    INBOUND_EVENT_DRIVER_APPLICATION,
    INBOUND_EVENT_RESERVATION_REQUEST,
    LOCATION_LEVELS,
    build_inbound_envelope,
    build_webhook_envelope,
    map_operational_point_to_public_location,
    map_vehicle_to_public_vehicle,
)
from .public_dtos import (
    build_public_airports,
    build_public_coverage,
    build_public_events,
    build_public_hotels,
    build_public_locations,
    build_public_statistics_legacy,
    build_public_stats,
    build_public_vehicles,
    find_public_location_by_slug,
)

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60
CACHE_MAX_AGE = 60

_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}


def api_gateway_url(app):
    host = os.environ.get(ENV_GATEWAY_HOST, "127.0.0.1")
    if getattr(app, "api_gateway_server", None):
        return f"http://{host}:{GATEWAY_PORT}"
    return start_api_gateway_server(app)


def _client_ip(handler) -> str:
    forwarded = handler.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return handler.client_address[0]


def _rate_limit_ok(ip: str) -> bool:
    now = time.monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    with _rate_lock:
        bucket = _rate_buckets.setdefault(ip, [])
        bucket[:] = [stamp for stamp in bucket if stamp >= cutoff]
        if len(bucket) >= RATE_LIMIT_REQUESTS:
            return False
        bucket.append(now)
    return True


def _state_file_mtime():
    path = os.path.join("data", "app_state.json")
    try:
        return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    except OSError:
        return datetime.now(timezone.utc)


def _legacy_published_vehicles(app):
    return [map_vehicle_to_public_vehicle(v) for v in _raw_published_vehicles(app)]


def _raw_published_vehicles(app):
    items = []
    for vehicle in getattr(app, "vehicles", []):
        if str(vehicle.get("status", "Ativo")).lower() not in {"ativo", "operando"}:
            continue
        if str(vehicle.get("portal_publicado", True)).lower() in {"nao", "false", "0"}:
            continue
        items.append(vehicle)
    return items


def _legacy_public_points(app):
    ensure_operational_network(app)
    from .operational_network import active_network_points

    return [map_operational_point_to_public_location(p) for p in active_network_points(app, public_only=True)]


def _filter_points_by_segment(points, segment):
    from .public_dtos import SEGMENT_TYPE_MAP

    allowed = SEGMENT_TYPE_MAP.get(segment, set())
    if not allowed:
        return []
    return [item for item in points if item.get("tipo") in allowed]


def _state_summaries(points):
    grouped = {}
    for point in points:
        uf = point.get("estado_uf", "")
        if not uf:
            continue
        entry = grouped.setdefault(
            uf,
            {
                "entity_type": ENTITY_STATE,
                "id": f"state-{uf}",
                "nome": uf,
                "estado_uf": uf,
                "operational_points": 0,
            },
        )
        entry["operational_points"] += 1
    return sorted(grouped.values(), key=lambda item: item.get("estado_uf", ""))


def _city_summaries(points, estado_uf=None):
    grouped = {}
    for point in points:
        uf = point.get("estado_uf", "")
        if estado_uf and uf != estado_uf.upper():
            continue
        city = point.get("cidade_nome", "")
        if not uf or not city:
            continue
        key = (uf, city)
        entry = grouped.setdefault(
            key,
            {
                "entity_type": ENTITY_CITY,
                "id": f"city-{uf}-{city}".lower().replace(" ", "-"),
                "nome": city,
                "estado_uf": uf,
                "cidade_nome": city,
                "operational_points": 0,
            },
        )
        entry["operational_points"] += 1
    return sorted(grouped.values(), key=lambda item: (item.get("estado_uf", ""), item.get("cidade_nome", "")))


def _find_by_slug_legacy(points, slug):
    slug = str(slug or "").strip().lower()
    for point in points:
        if str(point.get("website_slug", "")).lower() == slug:
            return point
    return None


def _extract_payload(body):
    if not body:
        return {}, ""
    data = json.loads(body)
    if not isinstance(data, dict):
        return {}, ""
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
    event = str(data.get("event") or payload.get("event") or "").strip()
    return payload, event


def _verify_secret(headers):
    secret = os.environ.get(ENV_GATEWAY_WEBHOOK_SECRET, "").strip()
    if not secret:
        return True
    provided = headers.get("X-Webhook-Secret") or headers.get("X-Integracao-Webhook-Secret")
    return str(provided or "").strip() == secret


PREFIX_BY_INBOUND_EVENT = {
    INBOUND_EVENT_COMPANY_LEAD: "clead",
    INBOUND_EVENT_DRIVER_APPLICATION: "dlead",
    INBOUND_EVENT_RESERVATION_REQUEST: "treq",
}


def process_inbound(app, event, payload):
    ensure_platform_collections(app)
    normalizer = INBOUND_NORMALIZERS.get(event)
    collection_name = INBOUND_COLLECTIONS.get(event)
    prefix = PREFIX_BY_INBOUND_EVENT.get(event)
    if not normalizer or not collection_name or not prefix:
        raise ValueError("unsupported_event")

    records = getattr(app, collection_name)
    record = normalizer({**payload, "origem": payload.get("origem") or ORIGIN_SITE})
    if not str(record.get("id", "")).startswith(f"{prefix}-"):
        record["id"] = next_record_id(prefix, records)
    records.insert(0, record)

    received_event = INBOUND_RECEIVED_EVENTS.get(event, "inbound.manual.created")
    log_event(
        app,
        received_event,
        f"Inbound {event}: {record.get('id', '')}",
        referencia_id=record.get("id", ""),
        origem=ORIGIN_SITE,
        payload=payload,
    )
    log_event(
        app,
        EVENT_LEAD_CREATED,
        "Lead/solicitacao registrada via gateway",
        referencia_id=record.get("id", ""),
        origem=ORIGIN_SITE,
    )

    if hasattr(app, "save_state"):
        app.save_state()

    notify_website(
        app,
        EVENT_LEAD_CREATED,
        event,
        record.get("id", ""),
        {"id": record.get("id", ""), "event": event},
    )
    return record


def notify_website(app, event, entity_type, entity_id, payload=None):
    url = os.environ.get(ENV_WEBHOOK_OUTBOUND_URL, "").strip()
    if not url:
        return False
    target_url = url.rstrip("/") + "/api/v1/webhooks/outbound/"
    envelope = build_webhook_envelope(event, entity_type, entity_id, payload)
    body = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        target_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    secret = os.environ.get(ENV_GATEWAY_WEBHOOK_SECRET, "").strip()
    if secret:
        request.add_header("X-Webhook-Secret", secret)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, OSError):
        return False


def _build_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def _send_json(self, code, payload, *, cacheable=True):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            etag = hashlib.sha256(body).hexdigest()
            last_modified = _state_file_mtime().strftime("%a, %d %b %Y %H:%M:%S GMT")

            if_none_match = self.headers.get("If-None-Match", "")
            if cacheable and if_none_match == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Last-Modified", last_modified)
                self.end_headers()
                return

            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            if cacheable:
                self.send_header("Cache-Control", f"public, max-age={CACHE_MAX_AGE}")
                self.send_header("ETag", etag)
                self.send_header("Last-Modified", last_modified)
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            return raw.decode("utf-8") if raw else "{}"

        def _query_param(self, query, *names):
            for name in names:
                values = query.get(name)
                if values and values[0]:
                    return values[0]
            return ""

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, X-Webhook-Secret, X-Integracao-Webhook-Secret",
            )
            self.end_headers()

        def do_GET(self):
            if not _rate_limit_ok(_client_ip(self)):
                return self._send_json(429, {"ok": False, "error": "rate_limit_exceeded"}, cacheable=False)

            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)

            if path in {API_PUBLIC_STATS, API_PUBLIC_STATISTICS}:
                if path == API_PUBLIC_STATS:
                    return self._send_json(200, build_public_stats(app))
                return self._send_json(200, build_public_statistics_legacy(app))

            if path == API_PUBLIC_COVERAGE:
                return self._send_json(200, build_public_coverage(app))

            if path == API_PUBLIC_VEHICLES:
                items = build_public_vehicles(app)
                return self._send_json(
                    200,
                    {"ok": True, "contract_version": CONTRACT_VERSION, "items": items, "total": len(items)},
                )

            if path == API_PUBLIC_AIRPORTS:
                items = build_public_airports(app)
                return self._send_json(
                    200,
                    {"ok": True, "contract_version": CONTRACT_VERSION, "items": items, "total": len(items)},
                )

            if path == API_PUBLIC_HOTELS:
                items = build_public_hotels(app)
                return self._send_json(
                    200,
                    {"ok": True, "contract_version": CONTRACT_VERSION, "items": items, "total": len(items)},
                )

            if path == API_PUBLIC_EVENTS:
                items = build_public_events(app)
                return self._send_json(
                    200,
                    {"ok": True, "contract_version": CONTRACT_VERSION, "items": items, "total": len(items)},
                )

            if path == API_PUBLIC_LOCATIONS_AGGREGATE:
                type_filter = self._query_param(query, "type", "tipo")
                state_filter = self._query_param(query, "state", "estado", "estado_uf", "uf")
                city_filter = self._query_param(query, "city", "cidade", "cidade_nome")
                items = build_public_locations(
                    app,
                    type_filter=type_filter or None,
                    state_filter=state_filter or None,
                    city_filter=city_filter or None,
                )
                return self._send_json(
                    200,
                    {"ok": True, "contract_version": CONTRACT_VERSION, "items": items, "total": len(items)},
                )

            if path.startswith(API_PUBLIC_LOCATION_DETAIL_BASE + "/"):
                slug = unquote(path[len(API_PUBLIC_LOCATION_DETAIL_BASE) + 1 :])
                item = find_public_location_by_slug(app, slug)
                if item:
                    return self._send_json(200, {"ok": True, "item": item})
                return self._send_json(404, {"ok": False, "error": "not_found"}, cacheable=False)

            if path.startswith(API_PUBLIC_LOCATIONS_BASE + "/"):
                suffix = unquote(path[len(API_PUBLIC_LOCATIONS_BASE) + 1 :])
                points = _legacy_public_points(app)

                if suffix in LOCATION_LEVELS:
                    if suffix == "states":
                        items = _state_summaries(points)
                    elif suffix == "cities":
                        uf = self._query_param(query, "estado_uf", "uf", "state").upper()
                        items = _city_summaries(points, uf or None)
                    else:
                        items = _filter_points_by_segment(points, suffix)
                    return self._send_json(
                        200,
                        {
                            "ok": True,
                            "contract_version": CONTRACT_VERSION,
                            "level": suffix,
                            "items": items,
                            "total": len(items),
                        },
                    )

                item = _find_by_slug_legacy(points, suffix)
                if item:
                    from .public_dtos import build_public_location_detail

                    return self._send_json(200, {"ok": True, "item": build_public_location_detail(item)})
                return self._send_json(404, {"ok": False, "error": "not_found"}, cacheable=False)

            net_result = handle_network_get(app, path, query)
            if net_result is not None:
                code, payload = net_result
                return self._send_json(code, payload, cacheable=False)

            return self._send_json(404, {"ok": False, "error": "not_found"}, cacheable=False)

        def do_POST(self):
            if not _rate_limit_ok(_client_ip(self)):
                return self._send_json(429, {"ok": False, "error": "rate_limit_exceeded"}, cacheable=False)

            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            raw = self._read_body()
            query = parse_qs(parsed.query)

            net_result = handle_network_post(app, path, raw, query)
            if net_result is not None:
                code, payload = net_result
                if code == 200 and hasattr(app, "save_state"):
                    app.save_state()
                return self._send_json(code, payload, cacheable=False)

            if not _verify_secret(self.headers):
                return self._send_json(401, {"ok": False, "error": "unauthorized"}, cacheable=False)

            if path == API_PUBLIC_SYNC_STATISTICS:
                summary = build_public_statistics_legacy(app)
                return self._send_json(
                    200,
                    {
                        "ok": True,
                        "contract_version": CONTRACT_VERSION,
                        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "statistics": summary,
                    },
                    cacheable=False,
                )

            if path == API_PUBLIC_SYNC_LOCATIONS:
                items = build_public_locations(app)
                return self._send_json(
                    200,
                    {
                        "ok": True,
                        "contract_version": CONTRACT_VERSION,
                        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "items": items,
                        "total": len(items),
                    },
                    cacheable=False,
                )

            inbound_map = {
                API_INBOUND_COMPANY_LEAD: INBOUND_EVENT_COMPANY_LEAD,
                API_INBOUND_DRIVER_APPLICATION: INBOUND_EVENT_DRIVER_APPLICATION,
                API_INBOUND_RESERVATION_REQUEST: INBOUND_EVENT_RESERVATION_REQUEST,
            }
            if path in inbound_map:
                try:
                    payload, event_hint = _extract_payload(raw)
                    event = event_hint or inbound_map[path]
                    record = process_inbound(app, event, payload)
                    envelope = build_inbound_envelope(
                        event,
                        event,
                        {
                            "id": record.get("id", ""),
                            **{k: record.get(k, "") for k in ("empresa", "nome", "origem", "destino") if k in record},
                        },
                    )
                    return self._send_json(200, {"ok": True, "id": record.get("id", ""), **envelope}, cacheable=False)
                except (json.JSONDecodeError, ValueError) as exc:
                    return self._send_json(400, {"ok": False, "error": str(exc) or "invalid_payload"}, cacheable=False)
                except Exception:
                    return self._send_json(500, {"ok": False, "error": "internal_error"}, cacheable=False)

            return self._send_json(404, {"ok": False, "error": "not_found"}, cacheable=False)

    return Handler


def start_api_gateway_server(app):
    if getattr(app, "api_gateway_server", None):
        host = os.environ.get(ENV_GATEWAY_HOST, "127.0.0.1")
        return f"http://{host}:{GATEWAY_PORT}"
    host = os.environ.get(ENV_GATEWAY_HOST, "127.0.0.1")
    try:
        server = ThreadingHTTPServer((host, GATEWAY_PORT), _build_handler(app))
    except OSError as exc:
        app.api_gateway_server = None
        app.api_gateway_bind_error = str(exc)
        print(f"[Gateway] Porta {GATEWAY_PORT} indisponivel ({exc}). Feche processos antigos ou altere GATEWAY_PORT.")
        return ""
    app.api_gateway_server = server
    threading.Thread(target=server.serve_forever, daemon=True, name="api-gateway-v1").start()
    return f"http://{host}:{GATEWAY_PORT}"
