"""Rotas web — Agenda (calendario de reservas, somente leitura)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.agenda_service import build_month_calendar

router = APIRouter(prefix="/agenda", tags=["master-agenda"])


@router.get("")
async def agenda_calendar(request: Request, year: int | None = None, month: int | None = None):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    reservations = getattr(runtime, "reservations", []) or []
    calendar_data = build_month_calendar(reservations, year, month)
    return templates.TemplateResponse(
        request,
        "master/agenda/calendar.html",
        template_context(
            request,
            admin=admin,
            active_nav="agenda",
            calendar=calendar_data,
        ),
    )
