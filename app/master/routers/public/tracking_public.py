"""Rotas publicas de rastreio — pagina INICIAR VIAGEM."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.tracking_links import STATUS_ACTIVE, STATUS_ENDED, STATUS_WAITING, TARGET_LABELS

from ...dependencies import get_runtime, template_context, templates
from ...services.geolocator_service import (
    append_position,
    end_trip,
    find_link_by_token,
    find_reservation_for_link,
    start_trip,
)

router = APIRouter(tags=["tracking-public"])


@router.get("/rastreio/{token}")
async def tracking_page(request: Request, token: str):
    runtime = get_runtime(request)
    link = find_link_by_token(runtime, token)
    if not link:
        return RedirectResponse("/", status_code=303)
    reservation = find_reservation_for_link(runtime, link)
    return templates.TemplateResponse(
        request,
        "master/geolocalizador/public.html",
        template_context(
            request,
            active_nav="",
            link=link,
            reservation=reservation or {},
            target_label=TARGET_LABELS.get(link.get("target_type"), link.get("target_type")),
            can_start=link.get("status") == STATUS_WAITING,
            is_active=link.get("status") == STATUS_ACTIVE,
            is_ended=link.get("status") == STATUS_ENDED,
        ),
    )


@router.post("/rastreio/{token}/iniciar")
async def tracking_start(request: Request, token: str):
    runtime = get_runtime(request)
    item, err = start_trip(runtime, token)
    if err:
        return JSONResponse({"ok": False, "error": err}, status_code=400)
    return JSONResponse({"ok": True, "status": item.get("status")})


@router.post("/rastreio/{token}/posicao")
async def tracking_position(request: Request, token: str):
    runtime = get_runtime(request)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    point, err = append_position(runtime, token, payload)
    if err:
        return JSONResponse({"ok": False, "error": err}, status_code=400)
    return JSONResponse({"ok": True, "position": point})


@router.post("/rastreio/{token}/encerrar")
async def tracking_end(request: Request, token: str):
    runtime = get_runtime(request)
    item, errors = end_trip(runtime, token)
    if errors:
        return JSONResponse({"ok": False, "error": errors[0]}, status_code=400)
    return JSONResponse({"ok": True, "status": item.get("status")})


@router.get("/rastreio/{token}/live")
async def tracking_live_json(request: Request, token: str):
    runtime = get_runtime(request)
    link = find_link_by_token(runtime, token)
    if not link:
        return JSONResponse({"ok": False}, status_code=404)
    return JSONResponse(
        {
            "ok": True,
            "status": link.get("status"),
            "last_position": link.get("last_position") or {},
            "positions_count": len(link.get("positions") or []),
        }
    )
