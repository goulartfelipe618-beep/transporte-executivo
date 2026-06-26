"""Redirecionamentos de URLs legadas (/painel/*) para rotas FastAPI atuais."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["master-legacy"])

# Slugs antigos do servidor sistema_web.py → paths do Master Web FastAPI
_LEGACY_SLUG_MAP = {
    "": "/dashboard",
    "dashboard": "/dashboard",
    "abrangencia": "/abrangencia",
    "agenda": "/agenda",
    "metricas": "/metricas",
    "financeiro": "/financeiro",
    "fin_dashboard": "/financeiro",
    "fin_lancamentos": "/financeiro/lancamentos",
    "fin_contas_pagar": "/financeiro/contas-a-pagar",
    "fin_contas_receber": "/financeiro/contas-a-receber",
    "fin_relatorios": "/financeiro/relatorios",
    "faturado": "/financeiro/faturado",
    "solicitacoes": "/solicitacoes",
    "reservas": "/reservas",
    "motoristas": "/motoristas",
    "empresas": "/empresas",
    "clientes": "/clientes",
    "veiculos": "/veiculos",
    "rede": "/rede",
    "configuracoes": "/configuracoes",
    "automacoes": "/automacoes",
    "leads_empresas": "/leads/empresas",
    "leads_motoristas": "/leads/motoristas",
}


def _resolve_legacy_target(slug: str) -> str:
    key = str(slug or "").strip().lower().replace("-", "_")
    return _LEGACY_SLUG_MAP.get(key, "/dashboard")


@router.get("/painel")
@router.get("/painel/")
async def legacy_panel_root(request: Request):
    return RedirectResponse("/dashboard", status_code=301)


@router.get("/painel/{slug:path}")
async def legacy_panel_slug(request: Request, slug: str):
    target = _resolve_legacy_target(slug.split("/")[0] if slug else "")
    return RedirectResponse(target, status_code=301)
