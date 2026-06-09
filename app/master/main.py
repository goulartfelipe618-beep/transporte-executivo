"""Aplicacao FastAPI do Centro Operacional Master."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .dependencies import STATIC_DIR
from .routers.api.health import router as health_router
from .routers.web.auth import router as auth_router
from .routers.web.dashboard import router as dashboard_router
from .routers.web.companies import router as companies_router
from .routers.web.drivers import router as drivers_router
from .routers.web.reservations import router as reservations_router
from .routers.web.vehicles import router as vehicles_router
from .routers.web.coverage import router as coverage_router
from .routers.web.transport_requests import router as transport_requests_router


def create_master_app(runtime_app) -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_build,
        docs_url=None,
        redoc_url=None,
    )
    app.state.runtime = runtime_app

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie,
        max_age=settings.session_max_age,
        same_site="lax",
        https_only=settings.https_only,
    )

    if STATIC_DIR.is_dir():
        app.mount("/static/master", StaticFiles(directory=str(STATIC_DIR)), name="master_static")

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(reservations_router)
    app.include_router(companies_router)
    app.include_router(drivers_router)
    app.include_router(vehicles_router)
    app.include_router(coverage_router)
    app.include_router(transport_requests_router)
    return app
