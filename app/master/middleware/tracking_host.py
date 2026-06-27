"""Middleware — dominio canonico rastreio.transporteexecutivo.com para Geolocalizador."""
from __future__ import annotations

from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.portal_urls import sistema_web_base, tracking_portal_base, tracking_portal_host

_LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def _request_host(request: Request) -> str:
    return (request.headers.get("host") or "").split(":")[0].lower()


def _host_from_base_url(base_url: str) -> str:
    return urlparse(base_url).netloc.split(":")[0].lower()


def _is_local_host(host: str) -> bool:
    return host in _LOCAL_HOSTS


def _is_tracking_host(host: str) -> bool:
    canonical = tracking_portal_host()
    return host == canonical or host == f"www.{canonical}"


def _is_sistema_host(host: str) -> bool:
    sistema = _host_from_base_url(sistema_web_base())
    return host == sistema or host == f"www.{sistema}"


def _redirect(url: str) -> Response:
    return RedirectResponse(url, status_code=301)


class TrackingHostMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = _request_host(request)
        path = request.url.path
        query = request.url.query
        suffix = f"?{query}" if query else ""

        if _is_local_host(host):
            return await call_next(request)

        if path.startswith("/rastreio") and not _is_tracking_host(host):
            target = f"{tracking_portal_base()}{path}{suffix}"
            return _redirect(target)

        if _is_tracking_host(host):
            allowed_prefixes = ("/rastreio", "/static/", "/health", "/api/health", "/api/deploy-info", "/favicon.ico")
            if path == "/" or not any(path.startswith(prefix) for prefix in allowed_prefixes):
                if path.startswith("/geolocalizador") or path.startswith("/login") or path.startswith("/dashboard"):
                    return _redirect(f"{sistema_web_base()}{path}{suffix}")
                if path == "/":
                    return _redirect(tracking_portal_base())

        return await call_next(request)
