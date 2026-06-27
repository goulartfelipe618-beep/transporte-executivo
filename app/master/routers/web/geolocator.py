"""Rotas web — Geolocalizador (links de rastreio)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.tracking_links import TARGET_CLIENTE, TARGET_MOTORISTA

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.delete_guard import delete_confirm_response, verify_delete_confirmation
from ...services.geolocator_service import (
    create_link,
    delete_link,
    eligible_reservations,
    end_trip,
    find_link_by_id,
    find_reservation_for_link,
    link_display,
    list_links,
    list_summary,
    live_payload,
    mark_communicated,
)
from app.portal_urls import tracking_portal_base

router = APIRouter(prefix="/geolocalizador", tags=["master-geolocator"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


@router.get("")
async def list_page(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/geolocalizador/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="geolocalizador",
            links=list_links(runtime),
            summary=list_summary(runtime),
            tracking_domain=tracking_portal_base(),
        ),
    )


@router.get("/novo")
async def create_form(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/geolocalizador/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="geolocalizador",
            reservations=eligible_reservations(runtime),
            form={},
            error="",
            target_cliente=TARGET_CLIENTE,
            target_motorista=TARGET_MOTORISTA,
            tracking_domain=tracking_portal_base(),
        ),
    )


@router.post("/novo")
async def create_submit(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    created_by = str((admin or {}).get("email") or (admin or {}).get("nome") or "")
    item, errors = create_link(runtime, form_data, created_by=created_by)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/geolocalizador/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="geolocalizador",
                reservations=eligible_reservations(runtime),
                form=form_data,
                error="; ".join(errors),
                target_cliente=TARGET_CLIENTE,
                target_motorista=TARGET_MOTORISTA,
                tracking_domain=tracking_portal_base(),
            ),
            status_code=400,
        )
    return RedirectResponse(f"/geolocalizador/{item['id']}?created=1", status_code=303)


@router.get("/api/reservas")
async def api_reservations(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return JSONResponse({"items": eligible_reservations(runtime)})


@router.get("/api/{link_id}/live")
async def api_live(request: Request, link_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    payload = live_payload(runtime, link_id)
    if not payload:
        return JSONResponse({"ok": False}, status_code=404)
    return JSONResponse({"ok": True, **payload})


@router.get("/{link_id}")
async def detail_page(request: Request, link_id: str, created: int = 0):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    link = find_link_by_id(runtime, link_id)
    if not link:
        return RedirectResponse("/geolocalizador", status_code=303)
    link = link_display(link)
    reservation = find_reservation_for_link(runtime, link)
    return templates.TemplateResponse(
        request,
        "master/geolocalizador/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="geolocalizador",
            link=link,
            reservation=reservation or {},
            created=bool(created),
            tracking_domain=tracking_portal_base(),
        ),
    )


@router.get("/{link_id}/acompanhar")
async def follow_page(request: Request, link_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    link = find_link_by_id(runtime, link_id)
    if not link:
        return RedirectResponse("/geolocalizador", status_code=303)
    reservation = find_reservation_for_link(runtime, link)
    return templates.TemplateResponse(
        request,
        "master/geolocalizador/follow.html",
        template_context(
            request,
            admin=admin,
            active_nav="geolocalizador",
            link=link,
            reservation=reservation or {},
        ),
    )


@router.post("/{link_id}/comunicar")
async def communicate_submit(request: Request, link_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    mark_communicated(runtime, link_id)
    return RedirectResponse(f"/geolocalizador/{link_id}?comunicado=1", status_code=303)


@router.post("/{link_id}/encerrar")
async def end_submit(request: Request, link_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    end_trip(runtime, link_id, by_admin=True)
    return RedirectResponse(f"/geolocalizador/{link_id}", status_code=303)


@router.get("/{link_id}/excluir")
async def delete_form(request: Request, link_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    link = find_link_by_id(runtime, link_id)
    if not link:
        return RedirectResponse("/geolocalizador", status_code=303)
    name = f"{link.get('cliente_nome') or link.get('reservation_numero')} · {link.get('target_label')}"
    entity_id = str(link.get("id", ""))
    return delete_confirm_response(
        request,
        admin,
        active_nav="geolocalizador",
        entity_title="Excluir link de rastreio",
        entity_name=name,
        entity_id=entity_id,
        cancel_url=f"/geolocalizador/{link_id}",
        post_url=f"/geolocalizador/{link_id}/excluir",
        warning_message="Esta acao e irreversivel. O link publico e o historico de posicoes serao apagados.",
    )


@router.post("/{link_id}/excluir")
async def delete_submit(request: Request, link_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    link = find_link_by_id(runtime, link_id)
    if not link:
        return RedirectResponse("/geolocalizador", status_code=303)

    form_data = _form_dict(await request.form())
    name = f"{link.get('cliente_nome') or link.get('reservation_numero')} · {link.get('target_label')}"
    entity_id = str(link.get("id", ""))
    ok, err = verify_delete_confirmation(form_data, entity_id)
    if not ok:
        return delete_confirm_response(
            request,
            admin,
            active_nav="geolocalizador",
            entity_title="Excluir link de rastreio",
            entity_name=name,
            entity_id=entity_id,
            cancel_url=f"/geolocalizador/{link_id}",
            post_url=f"/geolocalizador/{link_id}/excluir",
            warning_message="Esta acao e irreversivel. O link publico e o historico de posicoes serao apagados.",
            error=err,
            status_code=400,
        )
    delete_link(runtime, link_id)
    return RedirectResponse("/geolocalizador?success=Link+excluido", status_code=303)
