"""Servidor uvicorn em thread para o painel Master Web (porta 8772)."""
from __future__ import annotations

import threading

import uvicorn

from app.bind_host import bind_host, service_url

from .config import get_settings
from .main import create_master_app

_server_thread: threading.Thread | None = None


def start_master_web_server(runtime_app) -> str:
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        settings = get_settings()
        return service_url(settings.port)

    settings = get_settings()
    fastapi_app = create_master_app(runtime_app)
    host = bind_host()
    port = settings.port

    config = uvicorn.Config(
        fastapi_app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    def _run():
        server.run()

    _server_thread = threading.Thread(target=_run, name="master-web", daemon=True)
    _server_thread.start()
    print(f"[Nexus] Master Web FastAPI em {service_url(port)} (build {settings.app_build})")
    return service_url(port)
