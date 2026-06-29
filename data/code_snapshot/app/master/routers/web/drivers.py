"""Rotas web — CRUD de motoristas."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.delete_guard import delete_confirm_response, verify_delete_confirmation
from ...services.driver_portal_service import driver_reservations, portal_info, refresh_activation_token
from ...services.driver_service import (
    activate_driver,
    block_driver,
    create_driver,
    delete_driver,
    driver_display_name,
    driver_stats,
    find_driver_by_id_local,
    list_drivers,
    list_summary,
    update_driver,
)
from ...services.location_service import location_form_context
from ...validators.driver import CNH_CATEGORY_OPTIONS, FROTA_OPTIONS, PAYMENT_OPTIONS, normalize_driver_form, validate_driver_form

router = APIRouter(prefix="/motoristas", tags=["master-drivers"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


@router.get("")
async def list_drivers_page(request: Request, q: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/drivers/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="motoristas",
            drivers=list_drivers(runtime, search=q),
            search=q,
            summary=list_summary(runtime),
        ),
    )


@router.get("/novo")
async def create_form(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "master/drivers/form_create.html",
        template_context(
            request,
            admin=admin,
            active_nav="motoristas",
            frota_options=FROTA_OPTIONS,
            payment_options=PAYMENT_OPTIONS,
            cnh_category_options=CNH_CATEGORY_OPTIONS,
            **location_form_context({}),
            form={},
            error="",
        ),
    )


@router.post("/novo")
async def create_submit(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    form_data = normalize_driver_form(form_data)
    errors = validate_driver_form(form_data, is_create=True)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/drivers/form_create.html",
            template_context(
                request,
                admin=admin,
                active_nav="motoristas",
                frota_options=FROTA_OPTIONS,
                payment_options=PAYMENT_OPTIONS,
                cnh_category_options=CNH_CATEGORY_OPTIONS,
                **location_form_context(form_data),
                form=form_data,
                error=" ".join(errors),
            ),
            status_code=400,
        )
    driver = create_driver(runtime, form_data)
    return RedirectResponse(f"/motoristas/{driver.get('id')}?success=Motorista+cadastrado", status_code=303)


@router.get("/{driver_id}")
async def driver_detail(request: Request, driver_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    driver = find_driver_by_id_local(runtime, driver_id)
    if not driver:
        return RedirectResponse("/motoristas", status_code=303)
    stats = driver_stats(runtime, driver)
    reservations = driver_reservations(runtime, driver)
    portal = portal_info(driver)
    token_qs = request.query_params.get("token", "").strip()
    activation_token = token_qs or (portal.get("activation_token") if portal.get("activation_pending") else "")
    return templates.TemplateResponse(
        request,
        "master/drivers/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="motoristas",
            driver=driver,
            driver_name=driver_display_name(driver),
            stats=stats,
            portal=portal,
            reservations=reservations[:30],
            success_msg=request.query_params.get("success", ""),
            activation_token=activation_token,
        ),
    )


@router.get("/{driver_id}/editar")
async def edit_form(request: Request, driver_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    driver = find_driver_by_id_local(runtime, driver_id)
    if not driver:
        return RedirectResponse("/motoristas", status_code=303)
    return templates.TemplateResponse(
        request,
        "master/drivers/form_edit.html",
        template_context(
            request,
            admin=admin,
            active_nav="motoristas",
            driver=driver,
            frota_options=FROTA_OPTIONS,
            payment_options=PAYMENT_OPTIONS,
            cnh_category_options=CNH_CATEGORY_OPTIONS,
            **location_form_context(driver),
            portal=portal_info(driver),
            form=driver,
            error="",
        ),
    )


@router.post("/{driver_id}/editar")
async def edit_submit(request: Request, driver_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    driver = find_driver_by_id_local(runtime, driver_id)
    if not driver:
        return RedirectResponse("/motoristas", status_code=303)
    form_data = _form_dict(await request.form())
    form_data = normalize_driver_form(form_data)
    errors = validate_driver_form(form_data)
    if errors:
        return templates.TemplateResponse(
            request,
            "master/drivers/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="motoristas",
                driver=driver,
                frota_options=FROTA_OPTIONS,
                payment_options=PAYMENT_OPTIONS,
                cnh_category_options=CNH_CATEGORY_OPTIONS,
                **location_form_context(form_data),
                portal=portal_info(driver),
                form=form_data,
                error=" ".join(errors),
            ),
            status_code=400,
        )
    try:
        driver = update_driver(runtime, driver_id, form_data)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "master/drivers/form_edit.html",
            template_context(
                request,
                admin=admin,
                active_nav="motoristas",
                driver=driver,
                frota_options=FROTA_OPTIONS,
                payment_options=PAYMENT_OPTIONS,
                cnh_category_options=CNH_CATEGORY_OPTIONS,
                **location_form_context(form_data),
                portal=portal_info(driver),
                form=form_data,
                error=str(exc),
            ),
            status_code=400,
        )
    return RedirectResponse(f"/motoristas/{driver.get('id')}?success=Motorista+atualizado", status_code=303)


@router.get("/{driver_id}/excluir")
async def delete_form(request: Request, driver_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    driver = find_driver_by_id_local(runtime, driver_id)
    if not driver:
        return RedirectResponse("/motoristas", status_code=303)
    name = driver_display_name(driver)
    entity_id = str(driver.get("id", ""))
    return delete_confirm_response(
        request,
        admin,
        active_nav="motoristas",
        entity_title="Excluir motorista",
        entity_name=name,
        entity_id=entity_id,
        cancel_url=f"/motoristas/{driver_id}",
        post_url=f"/motoristas/{driver_id}/excluir",
        warning_message=(
            "Esta acao e irreversivel. O cadastro, portal, sessoes e vinculos do motorista serao removidos. "
            "Reservas existentes permanecem, mas ficam sem motorista atribuido."
        ),
    )


@router.post("/{driver_id}/excluir")
async def delete_submit(request: Request, driver_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    driver = find_driver_by_id_local(runtime, driver_id)
    if not driver:
        return RedirectResponse("/motoristas", status_code=303)

    form_data = _form_dict(await request.form())
    name = driver_display_name(driver)
    entity_id = str(driver.get("id", ""))
    ok, err = verify_delete_confirmation(form_data, entity_id)
    if not ok:
        return delete_confirm_response(
            request,
            admin,
            active_nav="motoristas",
            entity_title="Excluir motorista",
            entity_name=name,
            entity_id=entity_id,
            cancel_url=f"/motoristas/{driver_id}",
            post_url=f"/motoristas/{driver_id}/excluir",
            warning_message=(
                "Esta acao e irreversivel. O cadastro, portal, sessoes e vinculos do motorista serao removidos. "
                "Reservas existentes permanecem, mas ficam sem motorista atribuido."
            ),
            error=err,
            status_code=400,
        )
    try:
        delete_driver(runtime, driver_id)
    except ValueError:
        pass
    return RedirectResponse("/motoristas?success=Motorista+excluido", status_code=303)


@router.post("/{driver_id}/bloquear")
async def block_submit(request: Request, driver_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    try:
        block_driver(runtime, driver_id)
    except ValueError:
        pass
    return RedirectResponse("/motoristas", status_code=303)


@router.post("/{driver_id}/ativar")
async def activate_submit(request: Request, driver_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    driver = find_driver_by_id_local(runtime, driver_id)
    if not driver:
        return RedirectResponse("/motoristas", status_code=303)
    try:
        driver, token = activate_driver(runtime, driver_id, regenerate_token=True)
    except ValueError:
        return RedirectResponse(f"/motoristas/{driver_id}", status_code=303)
    url = f"/motoristas/{driver_id}?success=Motorista+ativado"
    if token:
        url += f"&token={token}"
    return RedirectResponse(url, status_code=303)


@router.get("/{driver_id}/portal")
async def portal_page(request: Request, driver_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    driver = find_driver_by_id_local(runtime, driver_id)
    if not driver:
        return RedirectResponse("/motoristas", status_code=303)
    portal = portal_info(driver)
    token_qs = request.query_params.get("token", "").strip()
    activation_token = token_qs or (portal.get("activation_token") if portal.get("activation_pending") else "")
    return templates.TemplateResponse(
        request,
        "master/drivers/detail.html",
        template_context(
            request,
            admin=admin,
            active_nav="motoristas",
            driver=driver,
            driver_name=driver_display_name(driver),
            stats=driver_stats(runtime, driver),
            portal=portal,
            reservations=[],
            success_msg="",
            activation_token=activation_token,
            portal_focus=True,
        ),
    )


@router.post("/{driver_id}/token")
async def regenerate_token_submit(request: Request, driver_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    driver = find_driver_by_id_local(runtime, driver_id)
    if not driver:
        return RedirectResponse("/motoristas", status_code=303)
    token = refresh_activation_token(driver)
    if hasattr(runtime, "save_state"):
        runtime.save_state()
    return RedirectResponse(f"/motoristas/{driver_id}?token={token}&success=Token+gerado", status_code=303)
