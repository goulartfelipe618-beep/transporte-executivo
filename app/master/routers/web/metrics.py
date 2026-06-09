"""Rotas web — Metricas e performance (somente leitura)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.metrics_page_service import metrics_page_context, metrics_reservations

router = APIRouter(prefix="/metricas", tags=["master-metrics"])


@router.get("")
async def metrics_page(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    reservations = metrics_reservations(runtime)
    ctx = metrics_page_context(reservations)
    return templates.TemplateResponse(
        request,
        "master/metricas/index.html",
        template_context(
            request,
            admin=admin,
            active_nav="metricas",
            **ctx,
        ),
    )
