"""Partner and Admin panel web UI."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["panels"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/partner", response_class=HTMLResponse)
@router.get("/partner/", response_class=HTMLResponse)
async def partner_panel(request: Request):
    return templates.TemplateResponse(request, "partner/dashboard.html")


@router.get("/partner/login", response_class=HTMLResponse)
async def partner_login(request: Request):
    return templates.TemplateResponse(request, "partner/login.html")


@router.get("/admin", response_class=HTMLResponse)
@router.get("/admin/", response_class=HTMLResponse)
async def admin_panel(request: Request):
    return templates.TemplateResponse(request, "admin/dashboard.html")


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse(request, "admin/login.html")
