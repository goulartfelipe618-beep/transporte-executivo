"""Rotas web — Financeiro (somente leitura, derivado de reservas)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.finance_service import finance_context, money_display

router = APIRouter(prefix="/financeiro", tags=["master-finance"])


def _base_context(request, admin, runtime, *, active_tab):
    ctx = finance_context(getattr(runtime, "reservations", []) or [])
    ctx.update(
        {
            "admin": admin,
            "active_nav": "financeiro",
            "active_finance_tab": active_tab,
            "gross_revenue_display": money_display(ctx["summary"]["gross_revenue"]),
            "received_display": money_display(ctx["summary"]["received"]),
            "to_receive_display": money_display(ctx["summary"]["to_receive"]),
            "to_pay_display": money_display(ctx["summary"]["to_pay"]),
            "net_result_display": money_display(ctx["summary"]["net_result"]),
            "total_repasse_display": money_display(ctx["summary"]["total_repasse"]),
            "average_ticket_display": money_display(ctx["summary"]["average_ticket"]),
            "net_positive": ctx["summary"]["net_result"] >= 0,
            "margin_positive": ctx["summary"]["margin_pct"] >= 0,
        }
    )
    return template_context(request, **ctx)


@router.get("")
async def finance_dashboard(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/financeiro/dashboard.html",
        _base_context(request, admin, runtime, active_tab="dashboard"),
    )


@router.get("/lancamentos")
async def finance_entries(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/financeiro/lancamentos.html",
        _base_context(request, admin, runtime, active_tab="lancamentos"),
    )


@router.get("/contas-a-pagar")
async def finance_payables(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/financeiro/contas_a_pagar.html",
        _base_context(request, admin, runtime, active_tab="pagar"),
    )


@router.get("/contas-a-receber")
async def finance_receivables(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/financeiro/contas_a_receber.html",
        _base_context(request, admin, runtime, active_tab="receber"),
    )


@router.get("/relatorios")
async def finance_reports(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/financeiro/relatorios.html",
        _base_context(request, admin, runtime, active_tab="relatorios"),
    )
