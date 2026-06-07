"""Entrada /{slug}/{codigo} — Gateway Master, sem PostgreSQL."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.clients.gateway_api import GatewayAPIError
from app.services.gateway_service import fetch_network, is_hotel_like, resolve_contributor_ref

router = APIRouter(tags=["partner-entry"])
templates = Jinja2Templates(directory="app/templates")

RESERVED = frozenset({
    "api", "static", "health", "express", "booking", "partner", "admin",
    "reservar", "docs", "redoc", "openapi.json",
})


@router.get("/{slug}/{codigo}", response_class=HTMLResponse)
async def network_booking_entry(slug: str, codigo: str, request: Request, ref: str | None = None):
    if slug.lower() in RESERVED:
        raise HTTPException(status_code=404, detail="Não encontrado")

    try:
        network = await fetch_network(slug, codigo)
    except GatewayAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail="Rede indisponível") from e

    request.session["network_slug"] = slug
    request.session["network_codigo"] = codigo
    request.session["network"] = network
    request.session["booking_flow"] = "express"
    request.session["contributor_ref"] = resolve_contributor_ref(network, ref)

    colors = network.get("colors") or {}
    return templates.TemplateResponse(
        request,
        "express/step1.html",
        {
            "step": 1,
            "flow": "express",
            "network": network,
            "is_hotel": is_hotel_like(network.get("type")),
            "default_origin": network.get("default_origin", ""),
            "contributor_ref": request.session.get("contributor_ref"),
            "branding": colors,
            "slug": slug,
            "codigo": codigo,
        },
    )
