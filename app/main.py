"""Motor de Reservas Nexus Transfer - FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from app.api.admin.router import router as admin_api_router
from app.api.partner.router import router as partner_api_router
from app.api.v1 import router as api_v1_router
from app.config import get_settings
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.trusted_host import ProductionHostMiddleware
from app.web.booking import router as booking_web_router
from app.web.express import router as express_web_router
from app.web.panels import router as panels_router
from app.web.partner_entry import router as partner_entry_router

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Motor de Reservas Nexus Transfer - api.transporteexecutivo.com",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="nexus_session",
    max_age=86400,
    same_site="lax",
    https_only=settings.is_production,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
if settings.is_production:
    app.add_middleware(ProductionHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(api_v1_router)
app.include_router(partner_api_router)
app.include_router(admin_api_router)
app.include_router(panels_router)
app.include_router(booking_web_router)
app.include_router(express_web_router)
app.include_router(partner_entry_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "motor-reservas-nexus",
        "database_configured": bool(settings.database_url.strip()),
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html")


@app.get("/reservar")
async def reservar_redirect():
    return RedirectResponse(url="/express/inicio", status_code=302)


@app.get("/booking/start", response_class=HTMLResponse)
async def booking_start(request: Request):
    return templates.TemplateResponse(
        request,
        "booking/search.html",
        {"partner": None, "csrf_token": "", "step": 1},
    )
