"""Dashboard operacional — metricas de reservas."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.metrics_service import build_metrics_stats

router = APIRouter(tags=["master-dashboard"])


@router.get("/painel")
async def painel_alias(request: Request):
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/dashboard")
async def dashboard(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    stats = build_metrics_stats(getattr(runtime, "reservations", []) or [])
    return templates.TemplateResponse(
        request,
        "master/dashboard.html",
        template_context(request, admin=admin, stats=stats, active_nav="dashboard"),
    )
